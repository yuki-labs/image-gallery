import os
import json
import time
from flask import Flask, render_template_string, send_from_directory, request, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
from PIL import Image

app = Flask(__name__)

# User should set this to the desired settings directory
SETTINGS_DIR = r""

# Global variable to store the last modified time of the image directory
last_modified_time = 0

def ensure_config_file():
    if SETTINGS_DIR is None:
        return False
    
    if not os.path.exists(SETTINGS_DIR):
        os.makedirs(SETTINGS_DIR)
    
    config_path = os.path.join(SETTINGS_DIR, 'config.json')
    if not os.path.exists(config_path):
        default_config = {
            "image_directory": "",
            "image_info": {}
        }
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=4)
    return True

def load_config():
    if not ensure_config_file():
        return None
    config_path = os.path.join(SETTINGS_DIR, 'config.json')
    with open(config_path, 'r') as f:
        return json.load(f)

def save_config(config):
    config_path = os.path.join(SETTINGS_DIR, 'config.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)

def shorten_filename(filename, max_length=20):
    name, ext = os.path.splitext(filename)
    if len(name) > max_length:
        return name[:max_length-3] + '...' + ext
    return filename

def get_image_dimensions(file_path):
    try:
        with Image.open(file_path) as img:
            return f"{img.width}x{img.height}"
    except:
        return "Unknown"

def get_images_from_directory(directory_path, image_info):
    images = []
    all_tags = set()
    if directory_path and os.path.exists(directory_path):
        for filename in os.listdir(directory_path):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                shortened = shorten_filename(filename)
                info = image_info.get(filename, {})
                tags = [tag.strip() for tag in info.get('tags', '').split(',') if tag.strip()]
                all_tags.update(tags)
                file_path = os.path.join(directory_path, filename)
                dimensions = get_image_dimensions(file_path)
                images.append({
                    'original': filename,
                    'shortened': shortened,
                    'info': info.get('info', ''),
                    'source': info.get('source', ''),
                    'tags': tags,
                    'dimensions': dimensions
                })
    return images, sorted(all_tags)

def get_directory_modified_time(directory_path):
    return os.path.getmtime(directory_path)

@app.route('/', methods=['GET', 'POST'])
def display_images():
    global last_modified_time
    
    if SETTINGS_DIR is None:
        return render_template_string(r'''
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Image Gallery - Configuration Required</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f0f0f0; }
                    h1 { color: #333; }
                    .warning { color: #ff0000; font-weight: bold; }
                    .info { color: #0000ff; }
                    .code { font-family: monospace; background-color: #f0f0f0; padding: 2px 4px; }
                </style>
            </head>
            <body>
                <h1>Image Gallery - Configuration Required</h1>
                <p class="warning">The SETTINGS_DIR is not configured. Please set it in the script before running.</p>
                <p class="info">To configure the script:</p>
                <ol>
                    <li>Open the script in a text editor.</li>
                    <li>Find the line <code class="code">SETTINGS_DIR = None</code></li>
                    <li>Replace <code class="code">None</code> with the full path to your settings directory, using a raw string (prefix with r).</li>
                    <li>Example for Unix/Linux: <code class="code">SETTINGS_DIR = r"/home/user/image_gallery_settings"</code></li>
                    <li>Example for Windows: <code class="code">SETTINGS_DIR = r"C:\Users\user\image_gallery_settings"</code></li>
                    <li>Save the script and run it again.</li>
                    <li>The script will automatically create a config.json file in the specified directory.</li>
                </ol>
            </body>
            </html>
        ''')
    
    config = load_config()
    if config is None:
        return "Failed to load or create configuration. Please check your settings directory permissions."

    if request.method == 'POST':
        new_image_dir = request.form['image_directory']
        if os.path.exists(new_image_dir):
            config['image_directory'] = new_image_dir
            save_config(config)
            last_modified_time = get_directory_modified_time(new_image_dir)
        else:
            return f"The directory '{new_image_dir}' does not exist. Please enter a valid directory path."

    images, all_tags = get_images_from_directory(config['image_directory'], config.get('image_info', {}))
    last_modified_time = get_directory_modified_time(config['image_directory'])

    return render_template_string(r'''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Image Gallery</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f0f0f0; }
                h1, h2 { color: #333; }
                .form-container { margin-bottom: 20px; }
                input[type="text"] { width: 300px; padding: 5px; }
                input[type="submit"] { padding: 5px 10px; background-color: #4CAF50; color: white; border: none; cursor: pointer; }
                .image-container { display: flex; flex-wrap: wrap; gap: 20px; }
                .image-item { 
                    background-color: white; 
                    border: 1px solid #ddd; 
                    border-radius: 4px; 
                    padding: 10px; 
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
                    cursor: pointer; 
                    position: relative;
                    width: 220px;
                    height: 220px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                }
                .image-item img { 
                    max-width: 200px; 
                    max-height: 200px; 
                    object-fit: contain;
                }
                .image-item p { margin: 10px 0 0; text-align: center; font-size: 14px; color: #666; }
                .modal { display: none; position: fixed; z-index: 1; left: 0; top: 0; width: 100%; height: 100%; overflow: hidden; background-color: rgba(0,0,0,0.9); }
                .modal-content { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); max-height: 100vh; width: auto; }
                .close { position: absolute; top: 15px; right: 35px; color: #f1f1f1; font-size: 40px; font-weight: bold; cursor: pointer; }
                .menu-icon { position: absolute; top: 5px; right: 5px; background-color: rgba(255,255,255,0.7); border-radius: 50%; width: 24px; height: 24px; text-align: center; line-height: 24px; cursor: pointer; }
                .menu-content { display: none; position: absolute; top: 30px; right: 5px; background-color: white; border: 1px solid #ddd; border-radius: 4px; padding: 10px; z-index: 1; }
                .menu-content textarea, .menu-content input[type="text"] { width: 200px; margin-bottom: 5px; }
                .menu-content textarea { height: 100px; }
                .menu-content button { margin-top: 5px; }
                .menu-content label { display: block; margin-top: 5px; }
                .tag-list { margin-bottom: 20px; }
                .tag { display: inline-block; background-color: #e0e0e0; padding: 5px 10px; margin: 2px; border-radius: 3px; cursor: pointer; }
                .tag.active { background-color: #4CAF50; color: white; }
                .button-container { display: flex; justify-content: space-between; margin-top: 10px; }
                .button-container button { flex: 1; margin: 0 5px; }
                .nav-button {
                    position: absolute;
                    top: 50%;
                    transform: translateY(-50%);
                    background-color: rgba(255,255,255,0.5);
                    border: none;
                    font-size: 24px;
                    padding: 10px;
                    cursor: pointer;
                }
                .nav-button:hover {
                    background-color: rgba(255,255,255,0.8);
                }
                #prevButton { left: 10px; }
                #nextButton { right: 10px; }
                .tooltip { 
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    width: 100%;
                    height: 100%;
                }
                .tooltip .tooltiptext { 
                    visibility: hidden; 
                    width: 120px; 
                    background-color: rgba(0, 0, 0, 0.7); 
                    color: #fff; 
                    text-align: center; 
                    border-radius: 6px; 
                    padding: 5px 0; 
                    position: absolute; 
                    z-index: 1; 
                    bottom: 100%; 
                    left: 50%; 
                    margin-left: -60px; 
                    opacity: 0; 
                    transition: opacity 0.3s;
                }
                .tooltip:hover .tooltiptext { 
                    visibility: visible; 
                    opacity: 1; 
                }
            </style>
        </head>
        <body>
            <h1>Image Gallery</h1>
            <div class="form-container">
                <form method="post">
                    <input type="text" name="image_directory" value="{{ image_directory }}" placeholder="Enter full image directory path">
                    <input type="submit" value="Update Image Directory">
                </form>
            </div>
            <h2>Images from: {{ image_directory }}</h2>
            <div class="tag-list">
                <strong>Tags:</strong>
                {% for tag in all_tags %}
                    <span class="tag" onclick="toggleTag(this)">{{ tag }}</span>
                {% endfor %}
            </div>
            <div class="image-container">
                {% for image in images %}
                    <div class="image-item" data-tags="{{ image.tags|join(',') }}">
                        <div class="tooltip">
                            <img src="{{ url_for('serve_image', filename=image.original) }}" alt="{{ image.shortened }}" onclick="openModal('{{ url_for('serve_image', filename=image.original) }}')">
                            <span class="tooltiptext">{{ image.dimensions }}</span>
                        </div>
                        <p title="{{ image.original }}">{{ image.shortened }}</p>
                        <div class="menu-icon" onclick="toggleMenu('{{ image.original }}')">⋮</div>
                        <div class="menu-content" id="menu-{{ image.original }}">
                            <label for="info-{{ image.original }}">Information:</label>
                            <textarea id="info-{{ image.original }}">{{ image.info }}</textarea>
                            <label for="source-{{ image.original }}">Source:</label>
                            <input type="text" id="source-{{ image.original }}" value="{{ image.source }}">
                            <label for="tags-{{ image.original }}">Tags (comma separated):</label>
                            <input type="text" id="tags-{{ image.original }}" value="{{ image.tags|join(', ') }}">
                            <div class="button-container">
                                <button onclick="saveImageInfo('{{ image.original }}')">Save</button>
                                <button onclick="cancelEdit('{{ image.original }}')">Cancel</button>
                            </div>
                        </div>
                    </div>
                {% else %}
                    <p>No images found in the specified directory.</p>
                {% endfor %}
            </div>

            <div id="imageModal" class="modal">
                <span class="close" onclick="closeModal()">&times;</span>
                <button id="prevButton" class="nav-button" onclick="navigateImage(-1)">&lt;</button>
                <img class="modal-content" id="modalImage">
                <button id="nextButton" class="nav-button" onclick="navigateImage(1)">&gt;</button>
            </div>

            <script>
                let currentImageIndex = 0;
                let images = [{% for image in images %}'{{ url_for('serve_image', filename=image.original) }}'{% if not loop.last %}, {% endif %}{% endfor %}];
                let imageInfo = {{ images|tojson|safe }};
                let lastModifiedTime = {{ last_modified_time }};

                function checkForUpdates() {
                    fetch('/check_updates')
                        .then(response => response.json())
                        .then(data => {
                            if (data.updated) {
                                updateGallery();
                            }
                        });
                }

                function updateGallery() {
                    fetch('/get_images')
                        .then(response => response.json())
                        .then(data => {
                            imageInfo = data.images;
                            images = data.images.map(img => `/images/${img.original}`);
                            updateImageContainer(data.images);
                            updateTagList(data.all_tags);
                            lastModifiedTime = data.last_modified_time;
                        });
                }

                function updateImageContainer(newImages) {
                    const container = document.querySelector('.image-container');
                    container.innerHTML = '';
                    newImages.forEach(image => {
                        const imageItem = createImageItem(image);
                        container.appendChild(imageItem);
                    });
                }

                function createImageItem(image) {
                    const imageItem = document.createElement('div');
                    imageItem.className = 'image-item';
                    imageItem.dataset.tags = image.tags.join(',');
                    imageItem.innerHTML = `
                        <div class="tooltip">
                            <img src="/images/${image.original}" alt="${image.shortened}" onclick="openModal('/images/${image.original}')">
                            <span class="tooltiptext">${image.dimensions}</span>
                        </div>
                        <p title="${image.original}">${image.shortened}</p>
                        <div class="menu-icon" onclick="toggleMenu('${image.original}')">⋮</div>
                        <div class="menu-content" id="menu-${image.original}">
                            <label for="info-${image.original}">Information:</label>
                            <textarea id="info-${image.original}">${image.info}</textarea>
                            <label for="source-${image.original}">Source:</label>
                            <input type="text" id="source-${image.original}" value="${image.source}">
                            <label for="tags-${image.original}">Tags (comma separated):</label>
                            <input type="text" id="tags-${image.original}" value="${image.tags.join(', ')}">
                            <div class="button-container">
                                <button onclick="saveImageInfo('${image.original}')">Save</button>
                                <button onclick="cancelEdit('${image.original}')">Cancel</button>
                            </div>
                        </div>
                    `;
                    return imageItem;
                }

                function updateTagList(newTags) {
                    const tagList = document.querySelector('.tag-list');
                    tagList.innerHTML = '<strong>Tags:</strong> ';
                    newTags.forEach(tag => {
                        const tagSpan = document.createElement('span');
                        tagSpan.className = 'tag';
                        tagSpan.textContent = tag;
                        tagSpan.onclick = function() { toggleTag(this); };
                        tagList.appendChild(tagSpan);
                    });
                }

                function openModal(imageSrc) {
                    var modal = document.getElementById("imageModal");
                    var modalImg = document.getElementById("modalImage");
                    modal.style.display = "block";
                    modalImg.src = imageSrc;
                    currentImageIndex = images.indexOf(imageSrc);
                    
                    modalImg.onload = function() {
                        var aspectRatio = this.naturalWidth / this.naturalHeight;
                        var maxHeight = window.innerHeight;
                        var maxWidth = window.innerWidth;
                        
                        if (aspectRatio > maxWidth / maxHeight) {
                            this.style.width = maxWidth + 'px';
                            this.style.height = 'auto';
                        } else {
                            this.style.height = maxHeight + 'px';
                            this.style.width = 'auto';
                        }
                    }
                }

                function closeModal() {
                    var modal = document.getElementById("imageModal");
                    modal.style.display = "none";
                }

                function navigateImage(direction) {
                    currentImageIndex = (currentImageIndex + direction + images.length) % images.length;
                    document.getElementById("modalImage").src = images[currentImageIndex];
                }

                function toggleMenu(imageId) {
                    var menu = document.getElementById('menu-' + imageId);
                    menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
                }

                function saveImageInfo(imageId) {
                    var info = document.getElementById('info-' + imageId).value;
                    var source = document.getElementById('source-' + imageId).value;
                    var tags = document.getElementById('tags-' + imageId).value;
                    fetch('/save_image_info', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            image_id: imageId,
                            info: info,
                            source: source,
                            tags: tags
                        }),
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'success') {
                            alert('Image info saved successfully!');
                            updateGallery();
                        } else {
                            alert('Failed to save image info.');
                        }
                    })
                    .catch((error) => {
                        console.error('Error:', error);
                        alert('An error occurred while saving image info.');
                    });
                }

                function cancelEdit(imageId) {
                    toggleMenu(imageId);
                }

                function toggleTag(tagElement) {
                    tagElement.classList.toggle('active');
                    filterImages();
                }

                function filterImages() {
                    var activeTags = Array.from(document.querySelectorAll('.tag.active')).map(tag => tag.textContent);
                    var images = document.querySelectorAll('.image-item');
                    
                    images.forEach(function(image) {
                        var imageTags = image.dataset.tags.split(',');
                        if (activeTags.length === 0 || activeTags.every(tag => imageTags.includes(tag))) {
                            image.style.display = '';
                        } else {
                            image.style.display = 'none';
                        }
                    });
                }

                document.addEventListener('keydown', function(event) {
                    if (document.getElementById("imageModal").style.display === "block") {
                        if (event.key === "ArrowLeft") {
                            navigateImage(-1);
                        } else if (event.key === "ArrowRight") {
                            navigateImage(1);
                        } else if (event.key === "Escape") {
                            closeModal();
                        }
                    }
                });

                window.onclick = function(event) {
                    var modal = document.getElementById("imageModal");
                    if (event.target == modal) {
                        modal.style.display = "none";
                    }
                }

                // Check for updates every 5 seconds
                setInterval(checkForUpdates, 5000);

                // Initial update
                updateGallery();
            </script>
        </body>
        </html>
    ''', images=images, image_directory=config['image_directory'], all_tags=all_tags, last_modified_time=last_modified_time)

@app.route('/images/<filename>')
def serve_image(filename):
    config = load_config()
    if config and 'image_directory' in config:
        return send_from_directory(config['image_directory'], secure_filename(filename))
    return "Configuration error", 500

@app.route('/save_image_info', methods=['POST'])
def save_image_info():
    config = load_config()
    if config is None:
        return jsonify({"status": "error", "message": "Failed to load configuration"}), 500

    data = request.json
    image_id = data.get('image_id')
    info = data.get('info')
    source = data.get('source')
    tags = data.get('tags')

    if not image_id or info is None or source is None or tags is None:
        return jsonify({"status": "error", "message": "Invalid data"}), 400

    if 'image_info' not in config:
        config['image_info'] = {}

    config['image_info'][image_id] = {
        'info': info,
        'source': source,
        'tags': tags
    }
    save_config(config)

    return jsonify({"status": "success"})

@app.route('/get_images')
def get_images():
    config = load_config()
    if config is None:
        return jsonify({"status": "error", "message": "Failed to load configuration"}), 500

    images, all_tags = get_images_from_directory(config['image_directory'], config.get('image_info', {}))
    last_modified_time = get_directory_modified_time(config['image_directory'])
    return jsonify({"images": images, "all_tags": all_tags, "last_modified_time": last_modified_time})

@app.route('/check_updates')
def check_updates():
    global last_modified_time
    config = load_config()
    if config is None:
        return jsonify({"status": "error", "message": "Failed to load configuration"}), 500

    current_modified_time = get_directory_modified_time(config['image_directory'])
    if current_modified_time > last_modified_time:
        last_modified_time = current_modified_time
        return jsonify({"updated": True})
    else:
        return jsonify({"updated": False})

if __name__ == '__main__':
    app.run(debug=True, port=5005)