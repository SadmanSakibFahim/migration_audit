import os
from pathlib import Path

def clear_bucket_logic(bucket_type):
    print(f"Clearing {bucket_type}...")
    try:
        if bucket_type == "config":
            config_file = Path("config/audit.yaml")
            if config_file.exists():
                config_file.unlink()
                print("Config cleared")
        
        elif bucket_type == "source":
            source_dir = Path("data/source")
            if source_dir.exists():
                for f in source_dir.iterdir():
                    if f.is_file():
                        f.unlink()
                print("Source cleared")
                
        elif bucket_type == "target":
            target_dir = Path("data/target")
            if target_dir.exists():
                for f in target_dir.iterdir():
                    if f.is_file():
                        f.unlink()
                print("Target cleared")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # 1. Create a dummy file in source
    os.makedirs("data/source", exist_ok=True)
    with open("data/source/test_clear.csv", "w") as f:
        f.write("test")
    
    print("Files before clear:")
    print(os.listdir("data/source"))
    
    # 2. Run clear logic
    clear_bucket_logic("source")
    
    print("Files after clear:")
    print(os.listdir("data/source"))
