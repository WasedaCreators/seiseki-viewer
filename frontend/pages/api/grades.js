import axios from 'axios';
import FormData from 'form-data';
import { IncomingForm } from 'formidable';
import fs from 'fs';
import http from 'http';

export const config = {
  api: {
    bodyParser: false,
  },
};

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ message: 'Method not allowed' });
  }

  try {
    // Parse the incoming form data
    const data = await new Promise((resolve, reject) => {
      const form = new IncomingForm();
      form.parse(req, (err, fields, files) => {
        if (err) return reject(err);
        resolve({ fields, files });
      });
    });

    const { fields } = data;
    
    // Prepare data for backend
    const formData = new FormData();
    // formidable v3 returns arrays for fields
    const username = Array.isArray(fields.username) ? fields.username[0] : fields.username;
    const password = Array.isArray(fields.password) ? fields.password[0] : fields.password;
    
    formData.append('username', username || '');
    formData.append('password', password || '');

    // Calculate length manually to ensure Content-Length header is correct
    const length = await new Promise((resolve, reject) => {
        formData.getLength((err, len) => {
            if (err) return reject(err);
            resolve(len);
        });
    });

    // Use a custom HTTP agent with keepAlive enabled
    const httpAgent = new http.Agent({ 
        keepAlive: true,
        keepAliveMsecs: 10000,
        timeout: 300000 // Socket timeout
    });

    // Determine backend URL from environment variable or default to localhost
    const backendUrl = process.env.BACKEND_URL || 'http://127.0.0.1:8001';

    // Forward to backend
    const backendResponse = await axios.post(`${backendUrl}/grades`, formData, {
      headers: {
        ...formData.getHeaders(),
        'Content-Length': length,
      },
      httpAgent,
      timeout: 300000, // 5 minutes timeout
      maxBodyLength: Infinity,
      maxContentLength: Infinity,
    });

    // Return backend response
    res.status(200).json(backendResponse.data);
  } catch (error) {
    console.error('Proxy error:', error.message);
    if (error.response) {
      res.status(error.response.status).json(error.response.data);
    } else {
      res.status(500).json({ message: 'Internal Server Error', error: error.message });
    }
  }
}
