import requests
import logging

class TrmnlUtils:
    def __init__(self, api_base, plugin_uuid):
        self.webhook_url = f"{api_base}/custom_plugins/{plugin_uuid}"

    def send_image_to_webhook(self, image_url):
        payload = {
            "merge_variables": {
                "image_url": image_url,
                "file_type": "image"
            }
        }
        try:
            requests.post(self.webhook_url, json=payload, headers={"Content-Type": "application/json"})
        except Exception as e:
            logging.error(f"Failed to send image URL to TRMNL: {e}")
            return False, str(e)
        return True, None
