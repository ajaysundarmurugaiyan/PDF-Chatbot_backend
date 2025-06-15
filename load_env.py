import os
from dotenv import load_dotenv

def load_environment():
    load_dotenv()
    # Optionally print or check if the key is loaded
    if os.environ.get('OPENAI_API_KEY'):
        print('OPENAI_API_KEY loaded successfully')
    else:
        print('OPENAI_API_KEY not found in environment')

if __name__ == "__main__":
    load_environment()
