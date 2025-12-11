import axios from 'axios';

export default async function handler(req, res) {
  const { id } = req.query;
  const backendUrl = process.env.BACKEND_URL || 'http://127.0.0.1:8001';
  const token = req.headers['x-admin-token'];

  if (req.method === 'DELETE') {
    try {
      const response = await axios.delete(`${backendUrl}/admin/data/${id}`, {
        headers: {
          'X-Admin-Token': token,
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
  } else if (req.method === 'PUT') {
    try {
      const response = await axios.put(`${backendUrl}/admin/data/${id}`, req.body, {
        headers: {
          'X-Admin-Token': token,
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
  } else {
    res.status(405).json({ message: 'Method not allowed' });
  }
}
