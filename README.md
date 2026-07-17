# 🎨 Send to DeviantArt — ComfyUI Node

Automatically publish your generated images to DeviantArt straight from ComfyUI.  
Generate an image → it gets uploaded to DeviantArt. No manual downloads, no browser tabs, no extra steps.

---

## ✨ Features

- 📤 Grabs the latest saved image from a folder and uploads it to DeviantArt
- 🔐 Handles authorization via browser (only needed once)
- 🔄 Remembers your login and refreshes tokens automatically
- 🏷️ Supports tags, gallery folders, mature content settings, watermarks, and more
- 📦 Can upload to Stash only (without publishing) — if you want to review first

---

## 📥 Installation

1. Copy the `DWA` folder into your `ComfyUI/custom_nodes/` directory:
   ```
   ComfyUI/custom_nodes/DWA/
   ```
2. Restart ComfyUI
3. The node **"🎨 Send to DeviantArt"** will appear in the **output** category

> 💡 Dependencies install automatically. If not — there's a `requirements.txt` in the folder.

---

## 🔧 First-Time Setup (once)

Before using the node, you need to create a DeviantArt app — takes about 2 minutes.

### Step 1 — Create a DeviantArt App

1. Go to [deviantart.com/developers/register](https://www.deviantart.com/developers/register)
2. Fill in the form:
   - **Title** — anything you want (e.g. "ComfyUI Uploader")
   - **OAuth2 Redirect URI** — enter exactly this: `http://localhost:8080/callback`
3. Click **Save**
4. You'll see two values — **Client ID** and **Client Secret**. Copy them somewhere safe

### Step 2 — Paste the keys into the node

Open the **🎨 Send to DeviantArt** node in ComfyUI and enter:
- `client_id` — your Client ID
- `client_secret` — your Client Secret

✅ That's it. No other configuration needed.

---

## 🚀 How to Use

1. Add the **🎨 Send to DeviantArt** node to your workflow
2. Connect your image output to the `images` input
3. Set `folder_path` to the folder where ComfyUI saves images (usually `output`)
4. Fill in `client_id` and `client_secret`
5. Set up tags and other options as you like
6. Run the workflow

### 🔑 First Run

On the first run, a browser window will open asking you to authorize on DeviantArt.  
Click **"Authorize"** — the browser will show "Authorization Successful!", you can close the tab.  
Done! You won't need to log in again.

---

## ⚙️ Node Settings

### Required

| Field | Description |
|-------|-------------|
| **images** | Connect the image output from another node here |
| **folder_path** | Folder where saved images are located (e.g. `output`) |
| **client_id** | Your DeviantArt app Client ID |
| **client_secret** | Your DeviantArt app Client Secret |

### Main Options

| Field | Description | Default |
|-------|-------------|---------|
| **tags** | Comma-separated tags (e.g. `digital art, ai generated, fantasy`) | `digital art, ai generated` |
| **title** | Title for the artwork. If left empty — auto-generated from filename | empty |
| **artist_comments** | Description for the artwork (HTML supported) | empty |
| **galleryids** | Gallery folder UUID (to publish to a specific folder) | empty |
| **display_resolution** | Max display resolution for viewers | Original |
| **publish_after_stash** | Publish immediately or just upload to Stash | Yes |

### 🔘 Toggles

| Field | What it does | Default |
|-------|-------------|---------|
| **is_ai_generated** | Mark as AI-generated | ✅ Yes |
| **is_mature** | Mark as mature / adult content | ❌ No |
| **feature** | Feature in your gallery feed | ✅ Yes |
| **allow_comments** | Allow comments | ✅ Yes |
| **allow_free_download** | Allow original file download | ✅ Yes |
| **add_watermark** | Add watermark | ❌ No |

### 🔞 Mature Content (when `is_mature` is enabled)

| Field | Description |
|-------|-------------|
| **mature_level** | Level: `moderate` or `strict` |
| **mature_nudity** | Contains nudity |
| **mature_sexual** | Sexual content |
| **mature_gore** | Violence / gore |
| **mature_language** | Strong language |
| **mature_ideology** | Ideological content |

---

## 🛠️ Troubleshooting

### ❌ "Authentication failed"
- Double-check your `client_id` and `client_secret`
- Make sure the redirect URI in your DeviantArt app settings is exactly `http://localhost:8080/callback`
- Check that port 8080 isn't being used by another app

### ❌ "No image files found"
- Make sure `folder_path` points to the correct directory
- Make sure the image has been saved before the node runs
- Supported formats: PNG, JPG, JPEG, GIF, BMP

### ❌ "Stash upload failed" or "Publish failed"
- Check your internet connection
- Try deleting `da_tokens.db` from the `DWA` folder and restarting (this triggers re-authorization)
- If you set `galleryids` — make sure the UUID is correct (or leave the field empty)

### 🔄 How to reset authorization
Delete the `da_tokens.db` file from the `DWA` folder. The browser will open again on the next run.

---

## 📄 License

MIT
