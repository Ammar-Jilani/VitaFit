import React, { useState } from 'react';
import './CalorieEstimation.css';

function CalorieEstimation() {
  const [loading, setLoading] = useState(false);
  const [showResult, setShowResult] = useState(false);
  const [image, setImage] = useState(null);

  const handleUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImage(URL.createObjectURL(file));
      setLoading(true);
      setShowResult(false);
      setTimeout(() => {
        setLoading(false);
        setShowResult(true);
      }, 2500); // Simulated backend delay
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

      {showResult && (
        <div className="result-card">
          <h2>Food Details</h2>
          <img src={image} alt="Uploaded" className="preview" />
          <ul>
            <li className="fade-li delay-1"><strong>Dish Name:</strong> Paneer Butter Masala</li>
            <li className="fade-li delay-2"><strong>Origin:</strong> Indian</li>
            <li className="fade-li delay-3"><strong>Calories:</strong> 320 kcal per serving</li>
            <li className="fade-li delay-4"><strong>Is it healthy?:</strong> Moderately</li>
            <li className="fade-li delay-5"><strong>Recommended weekly intake:</strong> 1–2 times</li>
          </ul>
        </div>
      )}
    </div>
  );
}

export default CalorieEstimation;
