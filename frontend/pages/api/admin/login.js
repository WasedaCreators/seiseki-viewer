import axios from 'axios';

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ message: 'Method not allowed' });
  }

  const backendUrl = process.env.BACKEND_URL || 'http://127.0.0.1:8001';

  try {
    const response = await axios.post(`${backendUrl}/admin/login`, req.body, {
      headers: {
        'Content-Type': 'application/json',
      },
    });
    res.status(200).json(response.data);
  } catch (error) {
    if (error.response) {
      res.status(error.response.status).json(error.response.data);
    } else {
      res.status(500).json({ message: 'Internal Server Error' });
    }
  }
}
