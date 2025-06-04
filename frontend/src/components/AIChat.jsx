// frontend/src/components/AIChat.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './AIChat.css';

const AIChat = ({ BACKEND_BASE_URL, sessionId }) => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [aiOverview, setAiOverview] = useState('');
    const [overviewLoading, setOverviewLoading] = useState(true);
    const [overviewError, setOverviewError] = useState('');

    // Extracts and formats error messages from API responses.
    const getErrorMessage = (errorData) => {
        if (errorData && errorData.detail) {
            if (typeof errorData.detail === 'string') {
                return errorData.detail;
            }
            if (Array.isArray(errorData.detail)) {
                return errorData.detail.map(err => {
                    const loc = err.loc ? err.loc.join('.') : 'unknown';
                    return `${loc} - ${err.msg}`;
                }).join('; ');
            }
        }
        return 'An unknown error occurred.';
    };

    // Fetches an initial health overview from the AI based on the session ID.
    useEffect(() => {
        const fetchAiOverview = async () => {
            if (!sessionId) {
                setOverviewLoading(false);
                return;
            }

            setOverviewLoading(true);
            setOverviewError('');

            try {
                const response = await axios.post(`${BACKEND_BASE_URL}/ai/overview`, {
                    session_id: sessionId,
                    message: "Please provide an initial health overview based on my fitness data."
                });

                setAiOverview(response.data.response);
                setMessages([{ sender: 'ai', text: response.data.response }]);
            } catch (error) {
                console.error('Error fetching AI health overview:', error.message);
                setOverviewError(`Error getting health overview: ${getErrorMessage(error.response?.data)}`);
                setMessages([{ sender: 'ai', text: `Failed to load initial overview: ${getErrorMessage(error.response?.data)}` }]);
            } finally {
                setOverviewLoading(false);
            }
        };

        fetchAiOverview();
    }, [sessionId, BACKEND_BASE_URL]);

    // Sends a user message to the AI chat and processes the AI's response.
    const sendMessage = async () => {
        if (input.trim() === '' || loading) return;

        const userMessage = { sender: 'user', text: input };
        setMessages((prevMessages) => [...prevMessages, userMessage]);
        setInput('');

        setLoading(true);

        try {
            const response = await axios.post(`${BACKEND_BASE_URL}/ai/chat`, {
                session_id: sessionId,
                message: userMessage.text
            });

            const aiResponse = { sender: 'ai', text: response.data.response };
            setMessages((prevMessages) => [...prevMessages, aiResponse]);

        } catch (error) {
            console.error('Error sending message to AI chat:', error);
            setMessages((prevMessages) => [...prevMessages, { sender: 'ai', text: `Error: ${getErrorMessage(error.response?.data)}` }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="ai-chat-container">
            <h3>AI Fitness Assistant</h3>
            <div className="chat-messages">
                {overviewLoading && <div className="message ai">Loading your health overview...</div>}
                {overviewError && <div className="message ai error-message">{overviewError}</div>}
                {!overviewLoading && messages.length === 0 && !overviewError && (
                    <div className="message ai">Hi there! Ask me anything about fitness or nutrition based on your plan.</div>
                )}
                {messages.map((msg, index) => (
                    <div key={index} className={`message ${msg.sender}`}>
                        {msg.text}
                    </div>
                ))}
                {loading && <div className="message ai">Thinking...</div>}
            </div>
            <div className="chat-input">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={(e) => { if (e.key === 'Enter') sendMessage(); }}
                    placeholder="Ask me anything..."
                    disabled={loading || overviewLoading || !sessionId}
                />
                <button onClick={sendMessage} disabled={loading || overviewLoading || !sessionId}>Send</button>
            </div>
        </div>
    );
};

export default AIChat;