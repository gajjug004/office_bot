frappe.ui.form.on("Office Bot Settings", {
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
