import requests

class ApiClient:
    def __init__(self, api_key, base_url="https://api.gnosisscan.io/api"):
        self.api_key = api_key
        self.base_url = base_url

    def fetch_token_transactions(self, address, contract_address=None, page=1, offset=1000, start_block=0, end_block=99999999, sort='asc'):
        """
        Fetch ERC20 token transfer events for a given address, optionally filtered by contract address.
        """
        params = {
            'module': 'account',
            'action': 'tokentx',
            'address': address,
            'page': page,
            'offset': offset,
            'startblock': start_block,
            'endblock': end_block,
            'sort': sort,
            'apikey': self.api_key
        }
        if contract_address:
            params['contractaddress'] = contract_address
        response = requests.get(self.base_url, params=params)
        response.raise_for_status()
        return response.json()