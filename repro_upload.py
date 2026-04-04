import httpx
import os

def test_upload():
    url = "http://127.0.0.1:8001/api/upload"
    token_url = "http://127.0.0.1:8001/api/token"
    
    # Create a dummy config file
    with open("test_config.yaml", "w") as f:
        f.write("tables: {}")
        
    with httpx.Client() as client:
        # Get JWT Token
        try:
            token_res = client.post(token_url, data={"username": "mega_admin", "password": "secure_pass"})
            print(f"Token status: {token_res.status_code}")
            if token_res.status_code != 200:
                print(f"Token error: {token_res.text}")
                return
            
            token = token_res.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Now try upload
            files = {
                "config": ("audit.yaml", open("test_config.yaml", "rb"), "application/x-yaml")
            }
            # source_files and target_files are empty
            
            res = client.post(url, headers=headers, files=files)
            print(f"Upload status: {res.status_code}")
            print(f"Upload body: {res.text}")
            
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    test_upload()
