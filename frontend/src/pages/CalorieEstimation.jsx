// frontend/CalorieEstimation.jsx

import React, { useState, useEffect } from 'react';
import './CalorieEstimation.css';

// Define the backend API URL. Use your actual AWS Public IP.
// IMPORTANT: Replace 'http://13.229.250.121:8000' with your actual AWS Fargate Public IP if it changes.
const API_BASE_URL = 'http://13.229.250.121:8000'; 

function CalorieEstimation() {
    const [loading, setLoading] = useState(false);
    const [showResult, setShowResult] = useState(false);
    const [imagePreviewUrl, setImagePreviewUrl] = useState(null); // Changed 'image' to 'imagePreviewUrl' for clarity
    const [detectionResults, setDetectionResults] = useState(null); // New state for storing API response
    const [error, setError] = useState(null); // New state for error handling

    // Clean up the object URL to prevent memory leaks
    useEffect(() => {
        return () => {
            if (imagePreviewUrl) {
                URL.revokeObjectURL(imagePreviewUrl);
            }
        };
    }, [imagePreviewUrl]);

    const handleUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) {
            return;
        }

        // Clear previous states
        setLoading(true);
        setShowResult(false);
        setDetectionResults(null);
        setError(null);
        setImagePreviewUrl(URL.createObjectURL(file)); // Set image preview immediately

        const formData = new FormData();
        formData.append('file', file); // 'file' must match the parameter name in your FastAPI endpoint (@app.post("/classify_dish", file: UploadFile = File(...)))

        try {
            const response = await fetch(`${API_BASE_URL}/classify_dish`, { // Updated URL
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                // If response is not OK (e.g., 400, 500 status)
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            setDetectionResults(data); // Store the entire response object
            setShowResult(true); // Show results section
            console.log('Detection results:', data); // Log the response for debugging

        } catch (err) {
            console.error('Error uploading image:', err);
            setError(err.message || 'Failed to analyze image. Please try again.'); // Display specific error message
            setShowResult(false); // Do not show results if there's an error
            setImagePreviewUrl(null); // Clear image preview on error
        } finally {
            setLoading(false); // Always stop loading, regardless of success or failure
        }
    };

    return (
        <div className="calorie-container">
            <div className="calorie-hero">
                <h1>Calorie Estimation</h1>
                <p>Upload your food image or type its name to get calorie insights</p>

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