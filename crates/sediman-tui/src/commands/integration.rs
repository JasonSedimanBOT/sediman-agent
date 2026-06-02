use sediman_tui_core::command::{Command, CommandCategory};

use crate::app::App;

pub async fn handle_connect(app: &mut App, args: &str) {
    let args = args.trim();

    if args.is_empty() {
        open_connect_picker(app).await;
        return;
    }

    let (service, rest) = match args.split_once(' ') {
        Some((s, r)) => (s.trim(), r.trim()),
        None => (args, ""),
    };

    match service {
        "discord" | "telegram" => {
            if rest.is_empty() {
                open_connect_picker(app).await;
                return;
            }
            let token = rest.to_string();
            match app
                .bridge
                .configure_integration(service, serde_json::json!({
                    "token": token,
                    "enabled": true,
                }))
                .await
            {
                Ok(_) => app.add_system_message(format!(
                    "{} integration enabled. Bot will start on next task.",
                    capitalize(service)
                )),
                Err(e) => app.add_error_message(format!("Failed to configure {}: {}", service, e)),
            }
        }
        _ => {
            app.add_error_message(format!(
                "Unknown service: {}. Use /connect to open the picker.",
                service
            ));
        }
    }
}

async fn open_connect_picker(app: &mut App) {
    match app.bridge.list_integrations().await {
        Ok(integrations) => {
            if integrations.is_empty() {
                app.add_error_message("No integrations available.".into());
                return;
            }
            app.connect_integration_list = integrations;
            app.connect_picker_idx = 0;
            app.connect_picker_scroll = 0;
            app.active_modal = Some(crate::app::AppModal::ConnectPicker);
        }
        Err(e) => app.add_error_message(format!("Failed to load integrations: {}", e)),
    }
}

fn capitalize(s: &str) -> String {
    let mut c = s.chars();
    match c.next() {
        None => String::new(),
        Some(f) => f.to_uppercase().collect::<String>() + c.as_str(),
    }
}

pub static CMD_CONNECT: Command = Command {
    name: "/connect",
    aliases: &[],
    description: "Connect integrations (Discord, Telegram)",
    category: CommandCategory::General,
};
