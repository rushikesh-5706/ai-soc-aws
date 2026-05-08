import React, { useEffect, useState } from 'react';
import axios from 'axios';
import {
  Shield,
  AlertTriangle,
  MessageSquare,
  LayoutDashboard,
  Activity,
  Send
} from 'lucide-react';

import './App.css';

const API_BASE_URL = 'https://1wls2elsr0.execute-api.us-east-1.amazonaws.com/prod';

function App() {

  const [incidents, setIncidents] = useState([]);
  const [stats, setStats] = useState({});
  const [message, setMessage] = useState('');
  const [chatMessages, setChatMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');

  useEffect(() => {
    fetchIncidents();
  }, []);

  const fetchIncidents = async () => {

    try {

      const res = await axios.get(`${API_BASE_URL}/incidents`);

      const data = res.data;

      if (typeof data.body === 'string') {

        const parsed = JSON.parse(data.body);

        setIncidents(parsed.incidents || []);
        setStats(parsed.stats || {});

      } else {

        setIncidents(data.incidents || []);
        setStats(data.stats || {});
      }

    } catch (err) {
      console.log(err);
    }
  };

  const sendMessage = async () => {

    if (!message.trim()) return;

    const userMessage = {
      sender: 'user',
      text: message
    };

    setChatMessages(prev => [...prev, userMessage]);

    setLoading(true);

    try {

      const res = await axios.post(`${API_BASE_URL}/chat`, {
        message: message
      });

      let aiText = 'No response from AI';
      if (res.data.body) {
        const parsedBody =
          typeof res.data.body === 'string'
          ? JSON.parse(res.data.body)
          : res.data.body;

      aiText =
      parsedBody.response ||
      parsedBody.message ||
      'No response from AI';
      } else {

      aiText =
      res.data.response ||
      res.data.message ||
      'No response from AI';
    }

    const aiReply = {
      sender: 'ai',
      text: aiText
    };

      setChatMessages(prev => [...prev, aiReply]);

    } catch (err) {

      setChatMessages(prev => [
        ...prev,
        {
          sender: 'ai',
          text: 'Error connecting to AI assistant.'
        }
      ]);

      console.log(err);
    }

    setMessage('');
    setLoading(false);
  };

  return (

    <div className="app-container">

      {/* SIDEBAR */}
      <div className="sidebar">

        <div className="logo-section">
          <Shield size={32} />
          <h2>AI SOC</h2>
        </div>

        <div className="menu-items">

          <div
            className={`menu-item ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            <LayoutDashboard size={20} />
            <span>Dashboard</span>
          </div>

          <div
            className={`menu-item ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            <MessageSquare size={20} />
            <span>AI Chat</span>
          </div>

          <div
            className={`menu-item ${activeTab === 'analytics' ? 'active' : ''}`}
            onClick={() => setActiveTab('analytics')}
          >
            <Activity size={20} />
            <span>Analytics</span>
          </div>

        </div>

      </div>

      {/* MAIN CONTENT */}
      <div className="main-content">

        {/* DASHBOARD TAB */}
        {activeTab === 'dashboard' && (

          <>

            {/* TOP CARDS */}
            <div className="stats-grid">

              <div className="stat-card">
                <h3>Total Incidents</h3>
                <p>{stats.total || 0}</p>
              </div>

              <div className="stat-card danger">
                <h3>Critical</h3>
                <p>{stats.critical || 0}</p>
              </div>

              <div className="stat-card warning">
                <h3>High Severity</h3>
                <p>{stats.high || 0}</p>
              </div>

              <div className="stat-card success">
                <h3>Auto Actioned</h3>
                <p>{stats.auto_actioned || 0}</p>
              </div>

            </div>

            {/* INCIDENT TABLE */}
            <div className="table-section">

              <div className="table-header">
                <AlertTriangle size={20} />
                <h2>Security Incidents</h2>
              </div>

              <table>

                <thead>
                  <tr>
                    <th>Incident</th>
                    <th>Severity</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>

                <tbody>

                  {incidents.map((incident, index) => (

                    <tr key={index}>
                      <td>{incident.alert_type}</td>
                      <td>{incident.severity}</td>
                      <td>{incident.status}</td>
                      <td>{incident.action_taken}</td>
                    </tr>

                  ))}

                </tbody>

              </table>

            </div>

          </>

        )}

        {/* CHAT TAB */}
        {activeTab === 'chat' && (

          <div className="table-section">

            <div className="table-header">
              <MessageSquare size={20} />
              <h2>AI Security Chat</h2>
            </div>

            <p style={{ color: '#9ca3af', marginTop: '20px' }}>
              Use the AI assistant panel on the right side to analyze incidents,
              investigate threats, automate SOC workflows, and generate
              security recommendations.
            </p>

          </div>

        )}

        {/* ANALYTICS TAB */}
        {activeTab === 'analytics' && (

          <div className="table-section">

            <div className="table-header">
              <Activity size={20} />
              <h2>Security Analytics</h2>
            </div>

            <div
              className="stats-grid"
              style={{ marginTop: '20px' }}
            >

              <div className="stat-card">
                <h3>False Positives</h3>
                <p>{stats.false_positives || 0}</p>
              </div>

              <div className="stat-card warning">
                <h3>Pending Review</h3>
                <p>{stats.pending_review || 0}</p>
              </div>

              <div className="stat-card success">
                <h3>Resolved Incidents</h3>
                <p>
                  {(stats.total || 0) - (stats.pending_review || 0)}
                </p>
              </div>

              <div className="stat-card danger">
                <h3>Threat Score</h3>
                <p>
                  {((stats.high || 0) * 10) + ((stats.critical || 0) * 20)}
                </p>
              </div>

            </div>

          </div>

        )}

      </div>

      {/* CHAT PANEL */}
      <div className="chat-panel">

        <div className="chat-header">
          <MessageSquare size={20} />
          <h3>AI Security Assistant</h3>
        </div>

        <div className="chat-body">

          {chatMessages.map((msg, index) => (

            <div
              key={index}
              className={`chat-message ${msg.sender}`}
            >
              {msg.text}
            </div>

          ))}

          {loading && (
            <div className="chat-message ai">
              Thinking...
            </div>
          )}

        </div>

        <div className="chat-input-section">

          <input
            type="text"
            placeholder="Ask AI about security incidents..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
          />

          <button onClick={sendMessage}>
            <Send size={18} />
          </button>

        </div>

      </div>

    </div>
  );
}

export default App;