// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

#[tauri::command]
fn get_api_endpoint() -> String {
    "http://127.0.0.1:8505".to_string()
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![get_api_endpoint])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
