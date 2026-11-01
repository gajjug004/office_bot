const PROVIDER_URLS = {
	OpenAI: "https://api.openai.com/v1",
	Anthropic: "https://api.anthropic.com/v1",
	OpenRouter: "https://openrouter.ai/api/v1",
	"Google Gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
};
const CUSTOM_PROVIDER = "Custom OpenAI-compatible";

frappe.ui.form.on("Office Bot Settings", {
	async onload(frm) {
		if (!frm.doc.ai_provider) {
			const provider = provider_from_url(frm.doc.ai_base_url) || "OpenRouter";
			frm._preserve_ai_model = true;
			frm._current_ai_provider = provider;
			await frm.set_value("ai_provider", provider);
			frm._preserve_ai_model = false;
		} else {
			frm._current_ai_provider = frm.doc.ai_provider;
		}
		update_ai_provider(frm);
		if (frm.doc.enable_ai) {
			load_provider_models(frm, true);
		}
	},

	ai_provider(frm) {
		const provider = frm.doc.ai_provider;
		const changed = frm._current_ai_provider && frm._current_ai_provider !== provider;
		if (changed && !frm._preserve_ai_model) {
			frm.set_value("ai_model", "");
			frm.fields_dict.ai_model.set_data([]);
			if (provider === CUSTOM_PROVIDER && Object.values(PROVIDER_URLS).includes(frm.doc.ai_base_url)) {
				frm.set_value("ai_base_url", "");
			}
		}
		frm._current_ai_provider = provider;
		update_ai_provider(frm);
		if (changed && !frm._preserve_ai_model && frm.doc.enable_ai) {
			load_provider_models(frm);
		}
	},

	async enable_ai(frm) {
		if (frm.doc.enable_ai) {
			load_provider_models(frm, true);
		}
	},

	ai_base_url(frm) {
		if (frm.doc.enable_ai && frm.doc.ai_provider === CUSTOM_PROVIDER && frm.doc.ai_base_url) {
			load_provider_models(frm);
		}
	},

	async load_ai_models(frm) {
		await load_provider_models(frm);
	},

	async connect_telegram(frm) {
		if (frm.is_dirty()) {
			await frm.save();
		}
		const { message: status } = await frappe.call({
			method: "office_bot.channels.telegram.connection_status",
			type: "GET",
		});

		if (status.this_site) {
			frappe.confirm(
				__(
					"Telegram is already connected to this site. Connect again to refresh the bot's command menu?"
				),
				() => connect_telegram(frm)
			);
		} else if (status.url) {
			frappe.confirm(
				__("This bot sends its messages to {0}. Move it to this site?", [
					`<b>${frappe.utils.escape_html(status.url)}</b>`,
				]),
				() => connect_telegram(frm)
			);
		} else {
			await connect_telegram(frm);
		}
	},
});

function provider_from_url(url = "") {
	const normalized = url.replace(/\/$/, "").toLowerCase();
	return Object.entries(PROVIDER_URLS).find(([_name, base_url]) => base_url.toLowerCase() === normalized)?.[0];
}

function update_ai_provider(frm) {
	const provider = frm.doc.ai_provider;
	const base_url = PROVIDER_URLS[provider];
	const is_custom = provider === CUSTOM_PROVIDER;
	frm.toggle_display("ai_base_url", is_custom);
	frm.set_df_property("ai_base_url", "reqd", is_custom && frm.doc.enable_ai);
	if (base_url && frm.doc.ai_base_url !== base_url) {
		frm.set_value("ai_base_url", base_url);
	}
}

async function load_provider_models(frm, quiet = false) {
	const provider = frm.doc.ai_provider;
	const base_url = frm.doc.ai_base_url;
	if (!provider || (provider === CUSTOM_PROVIDER && !base_url)) {
		if (!quiet) frappe.show_alert({ message: __("Enter the custom API URL first."), indicator: "orange" });
		return;
	}

	const request_id = (frm._ai_model_request_id || 0) + 1;
	frm._ai_model_request_id = request_id;
	let models;
	try {
		({ message: models } = await frappe.call({
			method: "office_bot.understand.list_models",
			args: { provider, base_url },
			freeze: !quiet,
			freeze_message: __("Loading models..."),
		}));
	} catch (error) {
		if (!quiet && request_id === frm._ai_model_request_id) {
			frappe.show_alert({
				message: __("Could not load the public model catalog. Try again later."),
				indicator: "red",
			});
		}
		return;
	}
	if (request_id !== frm._ai_model_request_id || provider !== frm.doc.ai_provider) return;

	const options = [...models];
	if (frm.doc.ai_model && !options.some(({ value }) => value === frm.doc.ai_model)) {
		options.unshift({ label: frm.doc.ai_model, value: frm.doc.ai_model });
	}
	frm.fields_dict.ai_model.set_data(options);
	if (!models.length) {
		if (!quiet) {
			frappe.show_alert({
				message: __("No matching models in the catalog. You can still enter a model ID."),
				indicator: "orange",
			});
		}
		return;
	}
	if (!quiet) {
		frm.fields_dict.ai_model.$input.trigger("focus").trigger("input");
		frappe.show_alert({
			message: __("Loaded {0} models", [models.length]),
			indicator: "green",
		});
	}
}

async function connect_telegram(frm) {
	const { message: url } = await frappe.call({
		method: "office_bot.channels.telegram.connect",
		freeze: true,
		freeze_message: __("Connecting to Telegram..."),
	});
	frappe.show_alert({
		message: __("Telegram now sends messages to {0}", [url]),
		indicator: "green",
	});
	frm.reload_doc();
}
