from brand_awareness_agent.src.brand_awareness_agent.main import BrandAwarenessFlow
from flask import Flask, request, jsonify, send_from_directory
import requests
import json
import datetime
import urllib
import os
import time
import openai
from dotenv import load_dotenv

load_dotenv()

fireCrawl = 'fc-a2b259bac59644d4a58c8beb33d27ac8'

app = Flask(__name__)
from flask_cors import CORS
CORS(app)

MAX_RETRIES = 3


def scrapeWithFireCrawl(url):
    base_url = "https://api.firecrawl.dev/v1/scrape"
    data = {
        "url": url,
        "formats": ["markdown", "links", "html", "rawHtml", "screenshot"],
        "includeTags": ["h1", "p", "a", ".main-content"],
        "excludeTags": ["#ad", "#footer"],
        "onlyMainContent": False,
        "waitFor": 10000,
        "timeout": 15000
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {fireCrawl}"
    }

    for attempt in range(MAX_RETRIES):
        print(f"Attempt {attempt + 1} to scrape URL: {url}")
        try:
            response = requests.post(base_url, headers=headers, json=data)
            dataGot = json.loads(response.text)
            print(f"Scraping successful: {dataGot}")
            
            with open(f"output/result.json", "w") as f:
                f.write(json.dumps(dataGot)) 

            return dataGot

        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt == MAX_RETRIES - 1:
                raise Exception(f"Error scraping after {MAX_RETRIES} attempts: {e}")
            time.sleep(2)  # optional wait before retrying
            
            break  # exit loop on success

        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt == MAX_RETRIES - 1:
                raise Exception(f"Error scraping after {MAX_RETRIES} attempts: {e}")
            time.sleep(2)  # optional wait before retrying

    return dataGot


def askGPTAgent(prompt):
    base_url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"
    }
    data = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    }
    response = requests.post(base_url, headers=headers, json=data)
    return response.text

@app.route('/', methods=['GET'])
def index():
    return jsonify({'message': 'Hello, World!'}), 200

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q')
    country = request.args.get('country')
    ad_type = request.args.get('ad_type')
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    try:
        fb_url = 'https://www.facebook.com/api/graphql/'
        headers = {
            'content-type': 'application/x-www-form-urlencoded',
        }

        variables = {
            'queryString': query,
            'isMobile': False,
            'country': country,
            'adType': ad_type
        }

        payload = {'fb_api_caller_class': 'RelayModern',
            'fb_api_req_friendly_name': 'useAdLibraryTypeaheadSuggestionDataSourceQuery',
            'variables': json.dumps(variables),
            'server_timestamps': 'true',
            'doc_id': '9333890689970605'}
        print('Outgoing data:', payload)  # Debug print
        response = requests.post(fb_url, headers=headers, data=payload)
        response.raise_for_status()
        fb_results = json.loads(response.text)
        return jsonify({'results': fb_results}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/page', methods=['GET'])
def page():
    brand = request.args.get('brand')
    page_id = request.args.get('page_id')
    ad_type = request.args.get('ad_type')
    country = request.args.get('country')

    print('Incoming data:', {brand, page_id, ad_type, country})

    if not page_id or not ad_type or not country:
        return jsonify({'error': 'Missing required parameters'}), 400

    try:
        fb_url = 'https://www.facebook.com/api/graphql/'
        headers = {
            'content-type': 'application/x-www-form-urlencoded',
        }

        cursor = ""
        ad_bodies = []
        count = 0

        while True:
            variables = {
                "activeStatus": "ACTIVE",
                "adType": ad_type,
                "bylines": [],
                "contentLanguages": [],
                "countries": [country],
                "cursor": cursor,
                "excludedIDs": [],
                "first": 30,
                "isTargetedCountry": False,
                "location": None,
                "mediaType": "ALL",
                "multiCountryFilterMode": None,
                "pageIDs": [],
                "potentialReachInput": [],
                "publisherPlatforms": [],
                "queryString": "",
                "regions": [],
                "searchType": "PAGE",
                "sortData": None,
                "source": None,
                "startDate": None,
                "v": "44b39a",
                "viewAllPageID": page_id
            }

            print("Variables - ", json.dumps(variables))

            payload = {
                'fb_api_caller_class': 'RelayModern',
                'fb_api_req_friendly_name': 'AdLibrarySearchPaginationQuery',
                'variables': json.dumps(variables),
                'server_timestamps': 'true',
                'doc_id': '9241757445859501'
            }

            response = requests.post(fb_url, headers=headers, data=payload)
            data = response.json()

            print("Response - ", json.dumps(data))

            try:
                edges = data['data']['ad_library_main']['search_results_connection']['edges']
                for edge in edges:
                    node = edge.get('node', {})
                    collated_results = node.get('collated_results', [])
                    for result in collated_results:
                        snapshot = result.get('snapshot', {})
                        body = snapshot.get('body', {})
                        text = body.get('text')
                        cta_type = snapshot.get('cta_type')
                        cta_text = snapshot.get('cta_text')
                        card_body = snapshot.get('cards', [])
                        video_url = snapshot.get('videos', [])
                        if text and len(card_body) == 0:
                            if video_url:
                                ad_bodies.append({"body": text, "cta_type": cta_type, "cta_text": cta_text, "asset": video_url[0]['video_hd_url']})
                            else:
                                ad_bodies.append({"body": text, "cta_type": cta_type, "cta_text": cta_text})
                        else:
                            print("Card Body")
                            for card in card_body:
                                card_text = card.get('body', {})
                                card_cta_type = card.get('cta_type')
                                card_cta_text = card.get('cta_text')
                                card_image_uri = card.get('original_image_url')
                                if card_text and card_cta_type and card_cta_text:
                                    ad_bodies.append({"body": card_text, "cta_type": card_cta_type, "cta_text": card_cta_text, "asset": card_image_uri})

                # Handle pagination
                page_info = data['data']['ad_library_main']['search_results_connection'].get('page_info', {})
                has_next_page = page_info.get('has_next_page')
                end_cursor = page_info.get('end_cursor')

                if has_next_page and end_cursor:
                    count += 1
                    cursor = end_cursor
                else:
                    break
                
                if count == 3:
                    break

            except Exception as e:
                print(f"Error navigating JSON: {e}")
                break
        
        print("Ad Bodies - ", ad_bodies)

        return jsonify({'ad_bodies': ad_bodies[:30]}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/brand', methods=['POST'])
def brand():
    ad_bodies = request.json.get('ad_bodies')
    ad_ctas = request.json.get('ad_ctas')
    brand = request.json.get('brand')
    print("Ad Bodies - ", ad_bodies)
    print("Ad CTAs - ", ad_ctas)
    print("Brand - ", brand)
    brand_awareness_flow = BrandAwarenessFlow()
    response = brand_awareness_flow.kickoff(inputs={"ad_copies": ad_bodies[:30], "brand_name": brand, "ad_ctas": ad_ctas[:30]})

    print(response)

    return jsonify({'response': response}), 200

@app.route('/wordware', methods=['POST'])
def wordware():
    try:
        data = request.json
        
        url = "https://app.wordware.ai/api/released-app/7f724839-fbe2-45be-a567-4a780203b625/run"
                

        payload = json.dumps({
            "inputs": {
                "human_prompt_start": data.get("human_prompt_start"),
                "linkedIn_brand_guidelines": data.get("linkedIn_brand_guidelines"),
                "feedback_input": data.get("feedback_input"),
                "link_to_article": data.get("article_link"),
                "feedback_bool": data.get("feedback_bool"),
                "previous_generated_body": data.get("previous_generated_body"),
                "previous_generated_cta": data.get("previous_generated_cta"),
                "file_upload": {
                    "type": "file",
                    "file_type": "application/pdf",
                    "file_url": request.host_url + "uploads/" + data.get("pdf_file_path"),
                    "file_name": data.get("pdf_file_path")
                },
                "file_upload_bool": data.get("file_upload_bool")
            },
            "version": "^4.5"
        })

        print("Payload - ", payload)
        
        headers = {
            'Authorization': 'Bearer ww-ECCqrRGp33jciiU6JWPYSCwI7yIz0XESRNKORcFtHR1y5lTNSF8Dyi',
            'Content-Type': 'application/json'
        }
        
        response = requests.request("POST", url, headers=headers, data=payload)
        ndjson_data = []
        
        if response.headers.get('Content-Type') == 'application/x-ndjson; charset=utf-8':
            for line in response.text.strip().split("\n"):
                try:
                    ndjson_data.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"Skipping invalid line: {line}")
        else:
            print("Unexpected content type:", response.headers.get('Content-Type'))
        
        return jsonify({
            'raw_response': ndjson_data,
            'status_code': response.status_code
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/upload-pdf', methods=['POST'])
def upload_pdf():
    try:
        data = request.get_json()
        if not data or 'fileName' not in data or 'base64Data' not in data:
            return jsonify({"error": "Missing required fields (fileName or base64Data)"}), 400

        file_name = data['fileName']
        base64_data = data['base64Data']
        
        # Create uploads directory if it doesn't exist
        upload_dir = 'uploads'
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)

        # Save the PDF file
        file_path = os.path.join(upload_dir, file_name)
        
        # Remove "data:application/pdf;base64," prefix if present
        if base64_data.startswith('data:application/pdf;base64,'):
            base64_data = base64_data.split(',')[1]

        # Decode and save the file
        try:
            import base64
            pdf_data = base64.b64decode(base64_data)
            with open(file_path, 'wb') as f:
                f.write(pdf_data)
        except Exception as e:
            return jsonify({"error": f"Failed to decode PDF: {str(e)}"}), 400

        # Return both the file name and path
        return jsonify({
            "message": "PDF uploaded successfully",
            "file_path": file_path,
            "file_name": file_name
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/uploads/<path:filename>')
def serve_pdf(filename):
    return send_from_directory('uploads', filename)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001, debug=True)
