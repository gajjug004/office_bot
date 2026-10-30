frappe.ui.form.on("Office Bot Settings", {
	async connect_telegram(frm) {
		if (frm.is_dirty()) {
			await frm.save();
		}
		const { message: url } = await frappe.call({
			method: "office_bot.channels.telegram.connect",
			freeze: true,
			freeze_message: __("Connecting to Telegram..."),
		});
		frappe.show_alert({ message: __("Telegram now sends messages to {0}", [url]), indicator: "green" });
		frm.reload_doc();
	},
});
