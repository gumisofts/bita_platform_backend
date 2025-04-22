import requests

url = "https://bita-dev-v01.s3.amazonaws.com/uploads/string.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAZDZTBYUTQ7KMXJ7F%2F20250418%2Feu-north-1%2Fs3%2Faws4_request&X-Amz-Date=20250418T224335Z&X-Amz-Expires=600&X-Amz-SignedHeaders=content-type%3Bhost&X-Amz-Signature=ef1734770eb15df010d97744733cf7f9f3a5eeac47ce80a4f0cea295e43368f1"

with open("/mnt/c/Users/murad/Downloads/string.jpg", "rb") as f:
    payload = f.read()
headers = {
    "User-Agent": "Apidog/1.0.0 (https://apidog.com)",
    "Content-Type": "image/jpeg",
    "Accept": "*/*",
    "Host": "bita-dev-v01.s3.amazonaws.com",
    "Connection": "keep-alive",
    "Referer": url,
}

response = requests.request("PUT", url, headers=headers, data=payload)

print(response.text)
print(response.headers)
