import telegram_bot_api from "@pipedream/telegram_bot_api";
import { axios } from "@pipedream/platform";
import { puppeteer } from "@pipedream/browsers";

// API configuration
const TELEGRAM_API_BASE = "https://api.telegram.org";
const TRMNL_API_BASE = "https://usetrmnl.com/api";

export default defineComponent({
  name: "Send Telegram PDF to TRMNL",
  description: "Convert PDF page to image and send to TRMNL device",
  type: "action",
  props: {
    telegram_bot_api,
    message: {
      type: "object",
      label: "Telegram Message",
      description: "The Telegram message object containing the PDF and caption",
    },
    plugin_url: {
      type: "string",
      label: "TRMNL Plugin UUID",
      description: "Paste your TRMNL plugin UUID (e.g. xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)",
    },
    filter_user_id: {
      type: "integer",
      label: "Filter User ID",
      description: "Optional. If set, only the user with this ID can use the bot. Leave empty to allow all users.",
      optional: true,
    },
  },

  methods: {
    // Permission validation
    validateUserPermission() {
      if (this.filter_user_id && this.message.from.id !== this.filter_user_id) {
        throw new Error("You don't have permission to use this bot.");
      }
    },

    // Extract PDF document from message
    getFileInfo($) {
      const document = this.message.document;
      if (document && document.mime_type === 'application/pdf') {
        return {
          file: document,
          type: 'pdf'
        };
      }
      
      throw new Error("No PDF document found in the message. Please send a PDF file.");
    },

    // Generate full file URL from Telegram
    async generateFileUrl($, file) {
      const fileInfo = await axios($, {
        url: `${TELEGRAM_API_BASE}/bot${this.telegram_bot_api.$auth.token}/getFile`,
        method: "GET",
        params: { file_id: file.file_id },
      });

      const filePath = fileInfo.result?.file_path;
      if (!filePath) {
        throw new Error("Can't find the file path from Telegram.");
      }

      return `${TELEGRAM_API_BASE}/file/bot${this.telegram_bot_api.$auth.token}/${filePath}`.trim();
    },

    // Parse caption for page number
    parseCaption() {
      const caption = this.message.caption || "";
      let pageNumber = 1;
      
      const pageCommandMatch = caption.match(/\/page\s+(\d+)/i);
      if (pageCommandMatch) {
        pageNumber = parseInt(pageCommandMatch[1]);
      }

      return { pageNumber };
    },

    // Convert PDF page to image using PDF-to-image conversion
    async convertPdfPageToImage($, pdfUrl, pageNumber) {
      const browser = await puppeteer.browser();
      
      try {
        const page = await browser.newPage();
        
        // Set viewport to match TRMNL's 800x480 resolution with higher DPI for sharp text
        await page.setViewport({
          width: 800,
          height: 480,
          deviceScaleFactor: 2  // Higher DPI for sharper text on e-ink
        });

        // Create an HTML page that uses PDF.js to render the PDF
        const html = `
          <!DOCTYPE html>
          <html>
          <head>
            <style>
              body { 
                margin: 0; 
                padding: 20px; 
                background: white; 
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                box-sizing: border-box;
              }
              canvas { 
                max-width: 100%;
                max-height: 100%;
                border: none;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
              }
              .loading {
                font-family: Arial, sans-serif;
                font-size: 18px;
                color: #666;
                text-align: center;
              }
            </style>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
          </head>
          <body>
            <div id="container">
              <div class="loading">Loading PDF page ${pageNumber}...</div>
            </div>
            
            <script>
              pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
              
              async function renderPDF() {
                try {
                  const container = document.getElementById('container');
                  
                  const pdf = await pdfjsLib.getDocument('${pdfUrl}').promise;
                  
                  if (${pageNumber} > pdf.numPages) {
                    container.innerHTML = '<div class="loading">Page ${pageNumber} not found. PDF has ' + pdf.numPages + ' pages.</div>';
                    window.pdfRendered = true;
                    return;
                  }
                  
                  const page = await pdf.getPage(${pageNumber});
                  const canvas = document.createElement('canvas');
                  const context = canvas.getContext('2d');
                  
                  // Calculate scale for optimal readability on 800x480 e-ink display
                  const viewport = page.getViewport({ scale: 1 });
                  
                  // Use a higher base scale for better text readability on small e-ink screen
                  const baseScale = 2.5;
                  const maxWidth = 760; // Leave 20px margin on each side
                  const maxHeight = 440; // Leave 20px margin top/bottom
                  
                  // Calculate scale to fit the 800x480 display while maintaining readability
                  const scaleToFitWidth = maxWidth / (viewport.width * baseScale);
                  const scaleToFitHeight = maxHeight / (viewport.height * baseScale);
                  const finalScale = Math.min(scaleToFitWidth, scaleToFitHeight, 1.2) * baseScale;
                  
                  const scaledViewport = page.getViewport({ scale: finalScale });
                  
                  canvas.height = scaledViewport.height;
                  canvas.width = scaledViewport.width;
                  
                  const renderContext = {
                    canvasContext: context,
                    viewport: scaledViewport
                  };
                  
                  await page.render(renderContext).promise;
                  
                  container.innerHTML = '';
                  container.appendChild(canvas);
                  
                  // Signal that rendering is complete
                  window.pdfRendered = true;
                  
                } catch (error) {
                  console.error('Error rendering PDF:', error);
                  document.getElementById('container').innerHTML = '<div class="loading">Error loading PDF: ' + error.message + '</div>';
                  window.pdfRendered = true;
                }
              }
              
              renderPDF();
            </script>
          </body>
          </html>
        `;

        await page.setContent(html);
        
        // Wait for PDF rendering to complete
        await page.waitForFunction(() => window.pdfRendered, { timeout: 30000 });
        
        // Take screenshot
        const imageBuffer = await page.screenshot({
          type: 'png',
          fullPage: false
        });

        return imageBuffer;
      } finally {
        await browser.close();
      }
    },

    // Upload image to Telegram and get URL
    async uploadImageToTelegram($, imageBuffer) {
      try {
        const chatId = this.message.chat.id;

        // Create form data with proper file object
        const formData = new FormData();
        formData.append('chat_id', chatId);
        formData.append('photo', new Blob([imageBuffer], { type: 'image/png' }), 'pdf-page.png');
        formData.append('caption', 'PDF page converted to image');

        const response = await axios($, {
          method: 'POST',
          url: `${TELEGRAM_API_BASE}/bot${this.telegram_bot_api.$auth.token}/sendPhoto`,
          data: formData,
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });

        console.log('Upload response:', response);

        // Check if we got a successful response from Telegram
        if (!response.result || !response.result.photo) {
          throw new Error('Failed to send photo to Telegram - no photo in response');
        }

        // Get the largest photo size
        const photos = response.result.photo;
        const largestPhoto = photos[photos.length - 1];

        // Now get the file URL
        const fileInfo = await axios($, {
          url: `${TELEGRAM_API_BASE}/bot${this.telegram_bot_api.$auth.token}/getFile`,
          method: "GET",
          params: { file_id: largestPhoto.file_id },
        });

        const filePath = fileInfo.result?.file_path;
        if (!filePath) {
          throw new Error("Can't get file path from Telegram for uploaded image");
        }

        const imageUrl = `${TELEGRAM_API_BASE}/file/bot${this.telegram_bot_api.$auth.token}/${filePath}`;
        console.log('✅ Image uploaded to Telegram:', imageUrl);
        
        return imageUrl;

      } catch (error) {
        console.error('Error uploading to Telegram:', error);
        console.error('Error details:', error.response?.data || error.message);
        
        // Fallback: return error image URL
        return 'https://http.cat/images/500.jpg';
      }
    },

    // Send image data to TRMNL
    async sendToTrmnl($, { imageUrl }) {
      const payload = {
        merge_variables: {
          image_url: imageUrl,
          file_type: "image"
        },
      };

      const response = await axios($, {
        method: "POST",
        url: `${TRMNL_API_BASE}/custom_plugins/${this.plugin_url}`,
        headers: { "Content-Type": "application/json" },
        data: payload,
      });

      console.log("📤 Payload Sent to TRMNL:", payload);
      console.log("📥 TRMNL Response:", response);

      return { response, payload };
    },
  },

  async run({ $ }) {
    try {
      this.validateUserPermission();
      const { file } = await this.getFileInfo($);
      const pdfUrl = await this.generateFileUrl($, file);
      const { pageNumber } = this.parseCaption();
      
      console.log(`🔄 Converting PDF page ${pageNumber} to image...`);
      const imageBuffer = await this.convertPdfPageToImage($, pdfUrl, pageNumber);
      
      console.log('📤 Uploading image to Telegram...');
      const imageUrl = await this.uploadImageToTelegram($, imageBuffer);
      
      const { response, payload } = await this.sendToTrmnl($, { imageUrl });

      $.export("$summary", `✅ PDF page ${pageNumber} converted and sent to TRMNL successfully.`);
      return {
        success: true,
        sent_payload: payload,
        response_from_trmnl: response,
        image_url: imageUrl
      };
    } catch (error) {
      const errorMessage = error.response?.data?.message || error.message;
      $.export("$summary", `❌ Error: ${errorMessage}`);
      return {
        success: true,
        error: {
          message: errorMessage,
          timestamp: new Date().toISOString()
        },
        shouldNotify: true
      };
    }
  },
});
