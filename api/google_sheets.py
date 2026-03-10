import gspread
from google.oauth2.service_account import Credentials


class GoogleSheetsPriceLoader:

    def __init__(self):
        self.credentials_path = "'/root/bot/bot/api/keycrm-prices-reader-b0f8fcd69a6f.json'"
        self.sheet_id = "1kuUmOVnh_ofoTrAjkwAzSpn3gWLfB04NcRKgphZk6AE"
        self.worksheet_name = "Аркуш1"

    def get_prices(self) -> dict:

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ]

        credentials = Credentials.from_service_account_file(
            self.credentials_path,
            scopes=scopes
        )

        client = gspread.authorize(credentials)

        worksheet = client.open_by_key(self.sheet_id).worksheet(self.worksheet_name)

        rows = worksheet.get_all_records()

        prices = {}

        for row in rows:

            sku = str(row.get("Артикул", "")).strip()
            partner_price = row.get("Ціна парнера")

            if not sku:
                continue

            if partner_price in (None, "", " "):
                continue

            try:
                prices[sku] = int(float(partner_price))
            except:
                continue

        return prices