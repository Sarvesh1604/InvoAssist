# 📦 InvoAssist

Invoice Query Assistant  

An AI assistant that allows users to interact and ask complex queries related to their purchase.

The invoice images are analyzed through AWS Textract and response is generated using Llama 3 Instruct (8B) model combined with LangChain's Buffer with summarizer (for storing conversation memory).

---

## ⚙️ Installation

```bash
# Clone the repository
git clone https://github.com/Sarvesh1604/InvoAssist.git
cd InvoAssist

# Install dependencies
pip install -r requirements.txt
```
### AWS Set-up
1. Download and Install AWS CLI V2 - [https://awscli.amazonaws.com/AWSCLIV2.msi]

2. Configure AWS CLI with your IAM user credentials
    ```sh
        aws configure
    ```
    ```sh
        AWS Access Key ID [None]: YOUR_ACCESS_KEY_ID
        AWS Secret Access Key [None]: YOUR_SECRET_ACCESS_KEY
        Default region name [None]: ap-south-1       # Or your preferred AWS region
    ```
### OpenRouter Setup
This project uses OpenRouter's API. You can get an API key by creating an account with [OpenRouter](https://openrouter.ai/) and plug it in 'utils/config.yaml'

---

## 🚀 Usage

```bash
# Run the Streamlit app
streamlit run app.py
```
> You can access the app at http://localhost:8501.

---

![UI](./test_data/ui_images/UI.png)