import os
from dotenv import load_dotenv

def load_environment():
    basedir = os.path.abspath(os.path.dirname(__file__))
    load_dotenv(os.path.join(basedir, '.env'))
    if os.environ.get('GROQ_API_KEY'):
        print('GROQ_API_KEY loaded successfully')
    else:
        print('GROQ_API_KEY not found in environment')

if __name__ == "__main__":
    load_environment()
