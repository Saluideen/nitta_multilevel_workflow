APP_NAME="nitta_note_app"

variable "FRAPPE_VERSION" {}
variable "ERPNEXT_VERSION" {}

group "default" {
    targets = ["backend", "frontend"]
}

target "backend" {
    dockerfile = "backend.Dockerfile"
    tags = ["nitta_note_app/worker:latest"]
    args = {
      "ERPNEXT_VERSION" = ERPNEXT_VERSION
      "APP_NAME" = APP_NAME
    }
}

target "frontend" {
    dockerfile = "frontend.Dockerfile"
    tags = ["nitta_note_app/nginx:latest"]
    args = {
      "FRAPPE_VERSION" = FRAPPE_VERSION
      "ERPNEXT_VERSION" = ERPNEXT_VERSION
      "APP_NAME" = APP_NAME
    }
}
