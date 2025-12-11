import { useState, useEffect } from 'react';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

export default function Admin() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [username, setUsername] = useState('');
  const [token, setToken] = useState('');
  const [data, setData] = useState([]);
  const [stats, setStats] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [editValue, setEditValue] = useState('');

  useEffect(() => {
    // Check cookie
    const cookies = document.cookie.split(';');
    const tokenCookie = cookies.find(c => c.trim().startsWith('admin_token='));
    if (tokenCookie) {
      const t = tokenCookie.split('=')[1];
      setToken(t);
      setIsLoggedIn(true);
      fetchData(t);
    }
  }, []);

  const handleLogin = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    try {
      const res = await axios.post('/api/admin/login', { username, token });
      if (res.data.status === 'success') {
        // Set cookie for 10 minutes (600 seconds)
        document.cookie = `admin_token=${token}; max-age=600; path=/`;
        setIsLoggedIn(true);
        fetchData(token);
      }
    } catch (err) {
      setErrorMsg('Login failed: Invalid credentials');
    }
  };

  const fetchData = async (authToken) => {
    try {
      const res = await axios.get('/api/admin/data', {
        headers: { 'X-Admin-Token': authToken }
      });
      if (res.data.status === 'success') {
        processData(res.data.data);
      }
    } catch (err) {
      console.error(err);
      if (err.response && err.response.status === 401) {
        setIsLoggedIn(false);
        document.cookie = 'admin_token=; max-age=0; path=/';
      }
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this record?')) return;
    try {
      await axios.delete(`/api/admin/student/${id}`, {
        headers: { 'X-Admin-Token': token }
      });
      fetchData(token);
    } catch (err) {
      alert('Delete failed');
    }
  };

  const startEdit = (row) => {
    setEditingId(row.student_id);
    setEditValue(row.avg_gpa);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditValue('');
  };

  const handleUpdate = async (id) => {
    try {
      await axios.put(`/api/admin/student/${id}`, { avg_gpa: parseFloat(editValue) }, {
        headers: { 'X-Admin-Token': token }
      });
      setEditingId(null);
      fetchData(token);
    } catch (err) {
      alert('Update failed');
    }
  };

  const processData = (rawData) => {
    // Calculate stats
    const scores = rawData.map(d => d.avg_gpa).filter(s => s !== null);
    
    if (scores.length === 0) {
        setData(rawData);
        return;
    }

    const mean = scores.reduce((a, b) => a + b, 0) / scores.length;
    const variance = scores.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / scores.length;
    const stdev = Math.sqrt(variance);

    // Calculate Rank and Deviation for each student
    const processed = rawData.map(d => {
        const score = d.avg_gpa;
        let deviation = 50;
        if (stdev > 0 && score !== null) {
            deviation = 50 + 10 * (score - mean) / stdev;
        }
        return { ...d, deviation, score };
    });

    // Calculate Rank
    // Sort by score desc
    const sorted = [...processed].sort((a, b) => (b.score || 0) - (a.score || 0));
    
    // Assign rank
    sorted.forEach((d, i) => {
        // Handle ties? Simple rank for now
        d.rank = i + 1;
    });

    // Re-sort by original order or ID? Let's keep sorted by rank for table
    setData(sorted);

    // Calculate Distribution for Graph (Histogram)
    const distData = [];
    const minScore = 0;
    const maxScore = 9.0;
    const step = 0.2;

    // Initialize bins
    const bins = {};
    // Create keys like "0.0", "0.2", ... "8.8", "9.0"
    for (let x = minScore; x < maxScore + step/2; x += step) {
        bins[x.toFixed(1)] = 0;
    }

    // Fill bins
    scores.forEach(s => {
        // Find closest lower bin
        // e.g. 2.35 -> 2.2
        const binVal = Math.floor(s / step) * step;
        // Clamp to maxScore just in case
        const clamped = Math.min(binVal, maxScore);
        const key = clamped.toFixed(1);
        if (bins[key] !== undefined) {
            bins[key]++;
        }
    });

    // Convert to array
    for (let x = minScore; x < maxScore + step/2; x += step) {
        const key = x.toFixed(1);
        distData.push({ score: key, count: bins[key] || 0 });
    }

    setStats({ mean, stdev, total: scores.length, distribution: distData });
  };

  if (!isLoggedIn) {
    return (
      <div className="container" style={{ maxWidth: '400px', margin: '50px auto', textAlign: 'center' }}>
        <h1>Admin Login</h1>
        <form onSubmit={handleLogin}>
          <div style={{ marginBottom: '10px' }}>
            <input
              type="text"
              placeholder="Username"
              value={username}
              onChange={e => setUsername(e.target.value)}
              style={{ width: '100%', padding: '8px' }}
            />
          </div>
          <div style={{ marginBottom: '10px' }}>
            <input
              type="password"
              placeholder="Token"
              value={token}
              onChange={e => setToken(e.target.value)}
              style={{ width: '100%', padding: '8px' }}
            />
          </div>
          <button type="submit" style={{ padding: '8px 16px' }}>Login</button>
        </form>
        {errorMsg && <p style={{ color: 'red' }}>{errorMsg}</p>}
      </div>
    );
  }

  return (
    <div className="container" style={{ maxWidth: '1000px', margin: '20px auto', padding: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>管理者画面</h1>
        <button onClick={() => {
            document.cookie = 'admin_token=; max-age=0; path=/';
            setIsLoggedIn(false);
        }}>ログアウト</button>
      </div>

      {stats && (
        <div style={{ marginBottom: '20px', padding: '20px', backgroundColor: '#f8f9fa', borderRadius: '8px', textAlign: 'center', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
            <h2 style={{ margin: 0, fontSize: '2.5rem', color: '#333' }}>成績平均: {stats.mean.toFixed(3)}</h2>
            <p style={{ margin: '5px 0 0 0', color: '#666' }}>データ数: {stats.total}</p>
        </div>
      )}

      {stats && (
        <div style={{ marginBottom: '40px' }}>
          <h2>成績分布</h2>
          <p>標準偏差: {stats.stdev.toFixed(3)}</p>
          <div style={{ width: '100%', height: 300 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stats.distribution}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="score" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#8884d8" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      <h2>データ詳細</h2>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #ccc' }}>
            <th style={{ textAlign: 'left', padding: '8px' }}>順位</th>
            <th style={{ textAlign: 'left', padding: '8px' }}>集計ID (ハッシュ済み)</th>
            <th style={{ textAlign: 'left', padding: '8px' }}>成績</th>
            <th style={{ textAlign: 'left', padding: '8px' }}>偏差値</th>
            <th style={{ textAlign: 'left', padding: '8px' }}>最終更新</th>
            <th style={{ textAlign: 'left', padding: '8px' }}>操作</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr key={row.student_id} style={{ borderBottom: '1px solid #eee' }}>
              <td style={{ padding: '8px' }}>{row.rank}</td>
              <td style={{ padding: '8px', fontFamily: 'monospace' }}>{row.student_id.substring(0, 10)}...</td>
              <td style={{ padding: '8px' }}>
                {editingId === row.student_id ? (
                  <input 
                    type="number" 
                    step="0.01" 
                    value={editValue} 
                    onChange={(e) => setEditValue(e.target.value)}
                    style={{ width: '60px' }}
                  />
                ) : (
                  row.avg_gpa?.toFixed(3)
                )}
              </td>
              <td style={{ padding: '8px' }}>{row.deviation?.toFixed(1)}</td>
              <td style={{ padding: '8px' }}>{row.timestamp}</td>
              <td style={{ padding: '8px' }}>
                {editingId === row.student_id ? (
                  <>
                    <button onClick={() => handleUpdate(row.student_id)} style={{ marginRight: '5px', color: 'green' }}>Save</button>
                    <button onClick={cancelEdit} style={{ color: 'gray' }}>Cancel</button>
                  </>
                ) : (
                  <>
                    <button onClick={() => startEdit(row)} style={{ marginRight: '5px', color: 'blue' }}>Edit</button>
                    <button onClick={() => handleDelete(row.student_id)} style={{ color: 'red' }}>Delete</button>
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
