import React, { useState, useEffect } from 'react';
import './FitnessPlanner.css';

function FitnessPlanner() {
  const [submitted, setSubmitted] = useState(false);
  const [showReport, setShowReport] = useState(false);
  const [showDietPlan, setShowDietPlan] = useState(false);

  const [formData, setFormData] = useState({
    name: '',
    mobile: '',
    email: '',
    age: '',
    gender: '',
    height: '',
    weight: '',
    bmi: '',
  });

  useEffect(() => {
    const heightInMeters = parseFloat(formData.height) / 100;
    const weightInKg = parseFloat(formData.weight);
    if (heightInMeters > 0 && weightInKg > 0) {
      const bmiValue = (weightInKg / (heightInMeters * heightInMeters)).toFixed(2);
      setFormData((prev) => ({ ...prev, bmi: bmiValue }));
    }
  }, [formData.height, formData.weight]);

  const handleSubmit = (e) => {
    e.preventDefault();
    setSubmitted(true);
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  return (
    <div className="fitness-bg">
      <div className="form-overlay">
        {!submitted ? (
          <>
            <h1 className="fade-text">Enter Your Details for Fitness Suggestions</h1>
            <form className="fitness-form" onSubmit={handleSubmit}>
  <input
    type="text"
    name="name"
    placeholder="👤 Full Name"
    value={formData.name}
    onChange={handleChange}
    required
  />
  <input
    type="tel"
    name="mobile"
    placeholder="📞 Mobile Number"
    value={formData.mobile}
    onChange={handleChange}
    required
  />
  <input
    type="email"
    name="email"
    placeholder="📧 Email"
    value={formData.email}
    onChange={handleChange}
    required
  />
  <input
    type="number"
    name="age"
    placeholder="🎂 Age"
    value={formData.age}
    onChange={handleChange}
    required
  />
  <select
    name="gender"
    value={formData.gender}
    onChange={handleChange}
    required
  >
    <option value="">⚧️ Select Gender</option>
    <option value="male">♂️ Male</option>
    <option value="female">♀️ Female</option>
    <option value="other">⚧️ Other</option>
  </select>
  <input
    type="number"
    name="height"
    placeholder="📏 Height (in cm)"
    value={formData.height}
    onChange={handleChange}
    required
  />
  <input
    type="number"
    name="weight"
    placeholder="⚖️ Weight (in kg)"
    value={formData.weight}
    onChange={handleChange}
    required
  />
  <input
    type="text"
    name="bmi"
    placeholder="📊 BMI (auto-calculated)"
    value={formData.bmi}
    readOnly
  />
  <button type="submit" className="animated-btn">✅ Submit</button>
</form>
          </>
        ) : !showReport ? (
          <div className="post-submit">
            <h2>VitaFit has processed your details.</h2>
            <h2>You can check your Daily Exercise Recommendation</h2>
            <p>(Based on Your Details)</p>
            <div className="report-buttons">
              <button className="animated-btn" onClick={() => setShowReport(true)}>
                Preview Exercise Recommendation Report
              </button>
            </div>
          </div>
        ) : (
          <div className={`report-wrapper ${showDietPlan ? 'with-diet-plan' : ''}`}>
            {/* Exercise Report */}
            <div className="recommendation-report fade-in-table">
              <h2>Daily Exercise Recommendation Report</h2>
              <table className="fitness-table">
               <thead>
  <tr>
    <th>🏃‍♂️ Exercise Type</th>
    <th>🔥 Intensity</th>
    <th>📅 Frequency</th>
    <th>⏱️ Duration</th>
    <th>⚡ Calorie Burn</th>
  </tr>
</thead>

                <tbody>
                  <tr>
                    <td>Brisk Walking</td>
                    <td>Low</td>
                    <td>5</td>
                    <td>30</td>
                    <td>120 kcal</td>
                  </tr>
                  
                </tbody>
              </table>

              <div className="report-buttons">
  <button className="animated-btn">
    Download This Exercise Recommendation Report (PDF)
  </button>

  {!showDietPlan && (
    <button className="animated-btn" onClick={() => setShowDietPlan(true)}>
      Wanna explore more? Preview Your VitaFit Suggested Diet Plan
    </button>
  )}
</div>

            </div>

            {/* Diet Plan */}
            {showDietPlan && (
              <div className="recommendation-report diet-plan slide-in">
                <h2>VitaFit Suggested Diet Plan</h2>
                <table className="fitness-table">
                 <thead>
  <tr>
    <th>🍽️ Calories/Day</th>
    <th>🥩 Protein (g)</th>
    <th>🍞 Carbs (g)</th>
    <th>🥑 Fats (g)</th>
  </tr>
</thead>

                  <tbody>
                    <tr>
                      <td>2200 kcal</td>
                      <td>120 g</td>
                      <td>280 g</td>
                      <td>70 g</td>
                    </tr>
                  </tbody>
                </table>

                <div className="diet-final-section">
                  <p>
                    Now based on your entered input, Exercise recommendation report and diet plan
                    report, VitaFit has made a complete fitness report for you.
                  </p>
                  <button className="animated-btn">Download Overall Fitness Report in PDF</button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default FitnessPlanner;
