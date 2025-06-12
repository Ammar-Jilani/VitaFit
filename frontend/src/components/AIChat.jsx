import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './AIChat.css';

const AIChat = ({ BACKEND_BASE_URL, sessionId }) => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [aiOverview, setAiOverview] = useState('');
    const [overviewLoading, setOverviewLoading] = useState(true);
    const [overviewError, setOverviewError] = useState('');
    const [showNewMessageBanner, setShowNewMessageBanner] = useState(false);

    const chatEndRef = useRef(null);
    const chatContainerRef = useRef(null);

    const getErrorMessage = (errorData) => {
        if (errorData?.detail) {
            if (typeof errorData.detail === 'string') return errorData.detail;
            if (Array.isArray(errorData.detail)) {
                return errorData.detail.map(err => {
                    const loc = err.loc ? err.loc.join('.') : 'unknown';
                    return `${loc} - ${err.msg}`;
                }).join('; ');
            }
        }
        return 'An unknown error occurred.';
    };

    const scrollToBottom = () => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const isUserAtBottom = () => {
        const el = chatContainerRef.current;
        return el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    };

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

    useEffect(() => {
        if (isUserAtBottom()) {
            scrollToBottom();
            setShowNewMessageBanner(false);
        } else {
            setShowNewMessageBanner(true);
        }
    }, [messages]);

    const handleScroll = () => {
        if (isUserAtBottom()) {
            setShowNewMessageBanner(false);
        }
    };

    const sendMessage = async () => {
        if (input.trim() === '' || loading) return;

        const userMessage = { sender: 'user', text: input };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setLoading(true);

        try {
            const response = await axios.post(`${BACKEND_BASE_URL}/ai/chat`, {
                session_id: sessionId,
                message: userMessage.text
            });

            const aiResponse = { sender: 'ai', text: response.data.response };
            setMessages(prev => [...prev, aiResponse]);
        } catch (error) {
            console.error('Error sending message:', error);
            setMessages(prev => [...prev, {
                sender: 'ai',
                text: `Error: ${getErrorMessage(error.response?.data)}`
            }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="ai-chat-container">
            <h3>AI Fitness Assistant</h3>

            <div
                className="chat-messages"
                ref={chatContainerRef}
                onScroll={handleScroll}
            >
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
                <div ref={chatEndRef} />
            </div>

            {showNewMessageBanner && (
                <div className="new-message-banner" onClick={scrollToBottom}>
                    ⬇ New message
                </div>
            )}

            <div className="chat-input">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                    placeholder="Ask me anything..."
                    disabled={loading || overviewLoading || !sessionId}
                />
                <button onClick={sendMessage} disabled={loading || overviewLoading || !sessionId}>Send</button>
            </div>
        </div>
    );
};

export default AIChat;
