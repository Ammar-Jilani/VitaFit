// frontend/CalorieEstimation.jsx

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './CalorieEstimation.css';

function CalorieEstimation() {
    // Defines the base URL for backend API interactions.
    const API_BASE_URL = 'http://localhost:8000';

    const [loading, setLoading] = useState(false);
    const [showResult, setShowResult] = useState(false);
    const [imagePreviewUrl, setImagePreviewUrl] = useState(null);
    const [detectionResults, setDetectionResults] = useState(null);
    const [error, setError] = useState(null);

    // Cleans up the image preview URL to prevent memory leaks.
    useEffect(() => {
        return () => {
            if (imagePreviewUrl) {
                URL.revokeObjectURL(imagePreviewUrl);
            }
        };
    }, [imagePreviewUrl]);

    // Handles the image upload, sends it to the backend for analysis, and displays results.
    const handleUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) {
            return;
        }

        setLoading(true);
        setShowResult(false);
        setDetectionResults(null);
        setError(null);
        setImagePreviewUrl(URL.createObjectURL(file));

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await axios.post(`${API_BASE_URL}/classify_dish`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });

            setDetectionResults(response.data);
            setShowResult(true);
            console.log('Detection results:', response.data);

        } catch (err) {
            console.error('Error uploading image:', err);
            setError(err.response?.data?.detail || err.message || 'Failed to analyze image. Please try again.');
            setShowResult(false);
            setImagePreviewUrl(null);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="calorie-container">
            <div className="calorie-hero">
                <h1>Calorie Estimation</h1>
                <p>Upload your food image to get calorie insights</p>

                <label htmlFor="image-upload" className="custom-upload">
                    📷 Upload Food Image
                </label>
                <input
                    id="image-upload"
                    type="file"
                    accept="image/*"
                    onChange={handleUpload}
                    hidden
                />
            </div>

            {loading && (
                <div className="loader-container">
                    <div className="loader"></div>
                    <p>Analyzing image... please wait</p>
                </div>
            )}

            {error && (
                <div className="error-card">
                    <h2>Error!</h2>
                    <p>{error}</p>
                    <p>Please ensure your backend is running and you have network access.</p>
                </div>
            )}

            {showResult && detectionResults && (
                <div className="result-card">
                    <h2>Food Details</h2>
                    <img src={imagePreviewUrl} alt="Uploaded" className="preview" />
                    {detectionResults.detections.length > 0 ? (
                        <ul>
                            {detectionResults.detections.map((detection, index) => (
                                <li key={index} className={`fade-li delay-${(index % 5) + 1}`}>
                                    <h3>{detection.class_name}</h3>
                                    <ul>
                                        <li><strong>Confidence:</strong> {detection.confidence * 100}%</li>
                                        <li><strong>Origin:</strong> {detection.origin || 'N/A'}</li>
                                        <li><strong>Description:</strong> {detection.description || 'No description available.'}</li>
                                        <li><strong>Estimated Calories:</strong> {detection.estimated_calories || 'N/A'}</li>
                                    </ul>
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <p>No known dishes detected in the image.</p>
                    )}
                </div>
            )}
        </div>
    );
}

export default CalorieEstimation;
