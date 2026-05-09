import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";

import {
  Shield,
  LayoutDashboard,
  MessageSquare,
  Activity,
  Bell,
  Search,
  Moon,
  Sun,
  Send
} from "lucide-react";

import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid
} from "recharts";

import "./App.css";

const API_BASE_URL =
  "https://1wls2elsr0.execute-api.us-east-1.amazonaws.com/prod";

function App() {

  // INCIDENT DATA

  const [incidents, setIncidents] = useState([]);

  const [stats, setStats] = useState({});

  const [graphData, setGraphData] = useState([]);

  const [pieData, setPieData] = useState([]);

  const [analyticsData, setAnalyticsData] = useState({});

  // UI STATES

  const [activeMenu, setActiveMenu] =
    useState("dashboard");

  const [darkMode, setDarkMode] =
    useState(true);

  const [chatOpen, setChatOpen] =
    useState(false);

  const [message, setMessage] =
    useState("");

  const [loading, setLoading] =
    useState(false);

  // SEARCH

  const [searchTerm, setSearchTerm] =
    useState("");

  // CHAT

  const [chatMessages, setChatMessages] =
    useState([
      {
        sender: "ai",
        text:
          "Hello 👋 I'm your AI SOC Assistant."
      }
    ]);

  // FETCH DATA

  useEffect(() => {
    fetchIncidents();
  }, []);

  const fetchIncidents = async () => {

    try {

      const response = await axios.get(
        `${API_BASE_URL}/incidents`
      );

      const data =
        typeof response.data.body === "string"
          ? JSON.parse(response.data.body)
          : response.data;

      setIncidents(data.incidents || []);

      setStats(data.stats || {});

      setGraphData(data.graphData || []);

      setPieData(data.pieData || []);

      setAnalyticsData(
        data.analytics || {}
      );

    } catch (error) {

      console.log(error);

    }
  };

  // SEARCH FILTER

  const filteredIncidents = useMemo(() => {

    return incidents.filter((item) => {

      const search =
        searchTerm.toLowerCase();

      return (
        item.alert_type
          ?.toLowerCase()
          .includes(search) ||

        item.severity
          ?.toLowerCase()
          .includes(search) ||

        item.status
          ?.toLowerCase()
          .includes(search) ||

        item.action_taken
          ?.toLowerCase()
          .includes(search)
      );
    });

  }, [searchTerm, incidents]);

  // AI CHAT

  const sendMessage = async () => {

    if (!message.trim()) return;

    const userMessage = {
      sender: "user",
      text: message
    };

    setChatMessages((prev) => [
      ...prev,
      userMessage
    ]);

    const currentMessage = message;

    setMessage("");

    setLoading(true);

    try {

      const response = await axios.post(
        `${API_BASE_URL}/chat`,
        {
          message: currentMessage
        }
      );

      let aiResponse =
        "No response from AI";

      if (response.data.body) {

        const parsed =
          typeof response.data.body ===
          "string"
            ? JSON.parse(
                response.data.body
              )
            : response.data.body;

        aiResponse =
          parsed.response ||
          parsed.answer ||
          aiResponse;

      } else {

        aiResponse =
          response.data.response ||
          response.data.answer ||
          aiResponse;
      }

      setChatMessages((prev) => [
        ...prev,
        {
          sender: "ai",
          text: aiResponse
        }
      ]);

    } catch (error) {

      console.log(error);

      setChatMessages((prev) => [
        ...prev,
        {
          sender: "ai",
          text:
            "Unable to connect to AI assistant."
        }
      ]);
    }

    setLoading(false);
  };

  const COLORS = [
    "#ff4d6d",
    "#ff9f1c",
    "#3a86ff",
    "#00d084"
  ];

  return (

    <div
      className={
        darkMode
          ? "app dark"
          : "app light"
      }
    >

      {/* SIDEBAR */}

      <div className="sidebar">

        <div>

          <div className="logo">

            <Shield size={34} />

            <div>
              <h2>AI SOC</h2>
              <p>Security Center</p>
            </div>

          </div>

          <div className="menu-list">

            <button
              className={
                activeMenu === "dashboard"
                  ? "menu-btn active"
                  : "menu-btn"
              }
              onClick={() =>
                setActiveMenu("dashboard")
              }
            >
              <LayoutDashboard size={20} />
              Dashboard
            </button>

            <button
              className={
                activeMenu === "chat"
                  ? "menu-btn active"
                  : "menu-btn"
              }
              onClick={() =>
                setActiveMenu("chat")
              }
            >
              <MessageSquare size={20} />
              AI Chat
            </button>

            <button
              className={
                activeMenu === "analytics"
                  ? "menu-btn active"
                  : "menu-btn"
              }
              onClick={() =>
                setActiveMenu("analytics")
              }
            >
              <Activity size={20} />
              Analytics
            </button>

          </div>

        </div>

        <button
          className="theme-btn"
          onClick={() =>
            setDarkMode(!darkMode)
          }
        >

          {darkMode ? (
            <Sun size={18} />
          ) : (
            <Moon size={18} />
          )}

          {darkMode
            ? "Light Mode"
            : "Dark Mode"}

        </button>

      </div>

      {/* MAIN */}

      <div className="main">

        {/* TOPBAR */}

        <div className="topbar">

          <div>

            <h1>
              Security Operations Dashboard
            </h1>

            <p>
              Monitor threats,
              incidents and AI powered
              analysis
            </p>

          </div>

          <div className="top-actions">

            {/* SEARCH */}

            <div className="search-box">

              <Search size={18} />

              <input
                type="text"
                placeholder="Search incidents..."
                value={searchTerm}
                onChange={(e) =>
                  setSearchTerm(
                    e.target.value
                  )
                }
              />

            </div>

            <button className="icon-btn">
              <Bell size={18} />
            </button>

            <button
              className="icon-btn"
              onClick={() =>
                setChatOpen(true)
              }
            >
              <MessageSquare size={18} />
            </button>

          </div>

        </div>

        {/* DASHBOARD */}

        {activeMenu === "dashboard" && (

          <>

            {/* STATS */}

            <div className="stats-grid">

              <div className="card">
                <h4>Total Incidents</h4>
                <h2>
                  {stats.total || 0}
                </h2>
              </div>

              <div className="card red">
                <h4>Critical</h4>
                <h2>
                  {stats.critical || 0}
                </h2>
              </div>

              <div className="card orange">
                <h4>High Severity</h4>
                <h2>
                  {stats.high || 0}
                </h2>
              </div>

              <div className="card green">
                <h4>Auto Actioned</h4>
                <h2>
                  {stats.auto_actioned || 0}
                </h2>
              </div>

            </div>

            {/* INCIDENT TABLE */}

            <div className="panel">

              <div className="panel-title">

                <Shield size={20} />

                <h3>
                  Security Incidents
                </h3>

              </div>

              <div className="table-wrapper">

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

                    {filteredIncidents.length >
                    0 ? (

                      filteredIncidents.map(
                        (
                          item,
                          index
                        ) => (

                          <tr key={index}>

                            <td>
                              {
                                item.alert_type
                              }
                            </td>

                            <td>
                              {
                                item.severity
                              }
                            </td>

                            <td>
                              {
                                item.status
                              }
                            </td>

                            <td>
                              {
                                item.action_taken
                              }
                            </td>

                          </tr>

                        )
                      )

                    ) : (

                      <tr>

                        <td
                          colSpan="4"
                          style={{
                            textAlign:
                              "center",
                            padding:
                              "30px"
                          }}
                        >
                          No incidents found
                        </td>

                      </tr>

                    )}

                  </tbody>

                </table>

              </div>

            </div>

          </>

        )}

        {/* CHAT */}

        {activeMenu === "chat" && (

          <div className="panel">

            <div className="panel-title">

              <MessageSquare size={22} />

              <h3>
                AI Security Assistant
              </h3>

            </div>

            <div className="chat-history-page">

              {chatMessages.map(
                (msg, index) => (

                  <div
                    key={index}
                    className={`chat-msg ${msg.sender}`}
                  >
                    {msg.text}
                  </div>

                )
              )}

            </div>

          </div>

        )}

        {/* ANALYTICS */}

        {activeMenu === "analytics" && (

          <div className="analytics-wrapper">

            {/* ANALYTICS CARDS */}

            <div className="analytics-page">

              <div className="analytics-box">

                <h2>
                  {analyticsData.accuracy ||
                    "98%"}
                </h2>

                <p>
                  Threat Detection
                  Accuracy
                </p>

              </div>

              <div className="analytics-box">

                <h2>
                  {analyticsData.response_time ||
                    "12s"}
                </h2>

                <p>
                  Average Response
                  Time
                </p>

              </div>

              <div className="analytics-box">

                <h2>
                  {analyticsData.monitoring ||
                    "24/7"}
                </h2>

                <p>
                  AI Monitoring
                </p>

              </div>

            </div>

            {/* CHARTS */}

            <div className="analytics-charts">

              {/* PIE */}

              <div className="panel">

                <div className="panel-title">

                  <Activity size={20} />

                  <h3>
                    Threat Distribution
                  </h3>

                </div>

                <ResponsiveContainer
                  width="100%"
                  height={320}
                >

                  <PieChart>

                    <Pie
                      data={pieData}
                      dataKey="value"
                      outerRadius={110}
                    >

                      {pieData.map(
                        (
                          entry,
                          index
                        ) => (

                          <Cell
                            key={index}
                            fill={
                              COLORS[
                                index %
                                  COLORS.length
                              ]
                            }
                          />

                        )
                      )}

                    </Pie>

                    <Tooltip />

                  </PieChart>

                </ResponsiveContainer>

              </div>

              {/* GRAPH */}

              <div className="panel">

                <div className="panel-title">

                  <Activity size={20} />

                  <h3>
                    Weekly Threat
                    Activity
                  </h3>

                </div>

                <ResponsiveContainer
                  width="100%"
                  height={320}
                >

                  <AreaChart
                    data={graphData}
                  >

                    <defs>

                      <linearGradient
                        id="gradient"
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="1"
                      >

                        <stop
                          offset="5%"
                          stopColor="#7b61ff"
                          stopOpacity={
                            0.8
                          }
                        />

                        <stop
                          offset="95%"
                          stopColor="#7b61ff"
                          stopOpacity={
                            0
                          }
                        />

                      </linearGradient>

                    </defs>

                    <CartesianGrid
                      strokeDasharray="3 3"
                    />

                    <XAxis dataKey="day" />

                    <YAxis />

                    <Tooltip />

                    <Area
                      type="monotone"
                      dataKey="incidents"
                      stroke="#7b61ff"
                      fill="url(#gradient)"
                    />

                  </AreaChart>

                </ResponsiveContainer>

              </div>

            </div>

          </div>

        )}

      </div>

      {/* FLOATING CHAT */}

      {chatOpen && (

        <div className="floating-chat">

          <div className="floating-header">

            <div>

              <h3>AI Assistant</h3>

              <p>
                Powered by Llama 3
              </p>

            </div>

            <button
              onClick={() =>
                setChatOpen(false)
              }
            >
              ✕
            </button>

          </div>

          <div className="floating-body">

            {chatMessages.map(
              (msg, index) => (

                <div
                  key={index}
                  className={`chat-msg ${msg.sender}`}
                >
                  {msg.text}
                </div>

              )
            )}

            {loading && (

              <div className="chat-msg ai">
                AI is thinking...
              </div>

            )}

          </div>

          <div className="floating-input">

            <input
              type="text"
              placeholder="Ask AI about cloud security..."
              value={message}
              onChange={(e) =>
                setMessage(
                  e.target.value
                )
              }
              onKeyDown={(e) =>
                e.key === "Enter" &&
                sendMessage()
              }
            />

            <button
              onClick={sendMessage}
            >
              <Send size={18} />
            </button>

          </div>

        </div>

      )}

    </div>
  );
}

export default App;