import React, { useState, useEffect } from 'react';
import './FitnessPlanner.css';
import { v4 as uuidv4 } from 'uuid'; // Import uuid library for session_id

function FitnessPlanner() {
    const [submitted, setSubmitted] = useState(false); // True after initial exercise prediction
    const [showDietInputForm, setShowDietInputForm] = useState(false); // To show optional diet input fields
    const [sessionId, setSessionId] = useState(''); // State to store the session ID
    const [exercisePlan, setExercisePlan] = useState(null); // State for exercise predictions
    const [dietPlan, setDietPlan] = useState(null); // State for diet predictions
    const [loadingPredictions, setLoadingPredictions] = useState(false); // Loading state for API call
    const [loadingDietPlan, setLoadingDietPlan] = useState(false); // New loading state for diet plan API call
    const [predictionError, setPredictionError] = useState(''); // Error state for initial prediction
    const [dietPredictionError, setDietPredictionError] = useState(''); // Error state for diet prediction

    const [formData, setFormData] = useState({
        name: '',
        mobile: '',
        email: '',
        age: '',
        gender: '',
        heightValue: '',
        heightUnit: 'cm',
        weightValue: '',
        weightUnit: 'kg',
        bmi: '', // auto-calculated
        caloriesIntake: '',
    });

    const [dietAdditionalDetails, setDietAdditionalDetails] = useState({
        medicalConditions: '',
        dietaryRestrictions: '',
        foodPreferences: '',
    });

    // Effect to calculate BMI
    useEffect(() => {
        const heightInCm = parseFloat(formData.heightValue);
        const weightInKg = parseFloat(formData.weightValue);

        let heightForBmi = 0;
        if (formData.heightUnit === 'cm') {
            heightForBmi = heightInCm / 100;
        } else if (formData.heightUnit === 'inches') {
            heightForBmi = (heightInCm * 2.54) / 100;
        } else if (formData.heightUnit === 'feet') {
            heightForBmi = (heightInCm * 30.48) / 100;
        }

        let weightForBmi = 0;
        if (formData.weightUnit === 'kg') {
            weightForBmi = weightInKg;
        } else if (formData.weightUnit === 'lbs') {
            weightForBmi = weightInKg * 0.453592;
        }

        if (heightForBmi > 0 && weightForBmi > 0) {
            const bmiValue = (weightForBmi / (heightForBmi * heightForBmi)).toFixed(2);
            setFormData((prev) => ({ ...prev, bmi: bmiValue }));
        } else {
            setFormData((prev) => ({ ...prev, bmi: '' }));
        }
    }, [formData.heightValue, formData.heightUnit, formData.weightValue, formData.weightUnit]);

    // Generate session ID on component mount
    useEffect(() => {
        setSessionId(uuidv4());
    }, []);

    const handleInitialSubmit = async (e) => {
        e.preventDefault();
        setLoadingPredictions(true);
        setPredictionError('');
        setDietPredictionError(''); // Clear diet error too

        // Prepare data for the backend's /predict_exercise endpoint
        const dataToSend = {
            session_id: sessionId,
            age: parseInt(formData.age),
            gender: formData.gender, // Send gender as 'male' or 'female' (lowercase)
            height_value: parseFloat(formData.heightValue),
            height_unit: formData.heightUnit,
            weight_value: parseFloat(formData.weightValue),
            weight_unit: formData.weightUnit,
            calories_intake: parseInt(formData.caloriesIntake),
            // Do NOT send optional diet fields here, they are for /predict_diet
        };

        try {
            const response = await fetch("http://localhost:8000/predict_exercise", { // Updated endpoint
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(dataToSend),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || "Failed to get exercise plan.");
            }

            const result = await response.json();
            console.log("Exercise prediction response:", result);
            setExercisePlan(result.exercise_plan);
            setDietPlan(null); // Ensure diet plan is reset for a new session/initial submission
            setSubmitted(true); // Indicate initial submission is complete
            setShowDietInputForm(false); // Hide diet input form initially
        } catch (error) {
            console.error("Exercise prediction error:", error.message);
            setPredictionError(error.message);
            alert(`There was a problem getting your exercise plan: ${error.message}`);
        } finally {
            setLoadingPredictions(false);
        }
    };

    const handleDietPrediction = async (e) => {
        e.preventDefault();
        setLoadingDietPlan(true);
        setDietPredictionError('');

        const dietDataToSend = {
            session_id: sessionId,
            medical_conditions: dietAdditionalDetails.medicalConditions,
            dietary_restrictions: dietAdditionalDetails.dietaryRestrictions,
            food_preferences: dietAdditionalDetails.foodPreferences,
        };

        try {
            const response = await fetch("http://localhost:8000/predict_diet", { // New endpoint
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(dietDataToSend),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || "Failed to get diet plan.");
            }

            const result = await response.json();
            console.log("Diet prediction response:", result);
            setDietPlan(result.diet_plan);
        } catch (error) {
            console.error("Diet prediction error:", error.message);
            setDietPredictionError(error.message);
            alert(`There was a problem getting your diet plan: ${error.message}`);
        } finally {
            setLoadingDietPlan(false);
        }
    };


    const handleDownloadReport = async () => {
        try {
            const userDetails = {
                first_name: formData.name.split(' ')[0] || '',
                last_name: formData.name.split(' ').slice(1).join(' ') || '',
                email: formData.email,
                phone: formData.mobile,
            };

            const response = await fetch("http://localhost:8000/generate_report", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    user_details: userDetails
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || "Failed to generate report");
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(new Blob([blob]));
            const link = document.createElement('a');
            link.href = url;
            const contentDisposition = response.headers.get('Content-Disposition');
            const filenameMatch = contentDisposition && contentDisposition.match(/filename="([^"]+)"/);
            const filename = filenameMatch ? filenameMatch[1] : `Fitness_Report_${sessionId}.pdf`;

            link.setAttribute('download', filename);
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error("Report download error:", error.message);
            alert(`There was a problem downloading the report: ${error.message}`);
        }
    };

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData((prev) => ({
            ...prev,
            [name]: value,
        }));
    };

    const handleDietDetailsChange = (e) => {
        const { name, value } = e.target;
        setDietAdditionalDetails((prev) => ({
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
                        <form className="fitness-form" onSubmit={handleInitialSubmit}> {/* Updated onSubmit */}
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
                                <option value="male">♂️ Male</option> {/* Corrected to lowercase 'male' */}
                                <option value="female">♀️ Female</option> {/* Corrected to lowercase 'female' */}
                            </select>

                            {/* Height Input with Unit Selection */}
                            <div className="input-group">
                                <input
                                    type="number"
                                    name="heightValue"
                                    placeholder="📏 Height"
                                    value={formData.heightValue}
                                    onChange={handleChange}
                                    required
                                />
                                <select
                                    name="heightUnit"
                                    value={formData.heightUnit}
                                    onChange={handleChange}
                                    className="unit-select"
                                >
                                    <option value="cm">cm</option>
                                    <option value="inches">inches</option>
                                    <option value="feet">feet</option>
                                </select>
                            </div>

                            {/* Weight Input with Unit Selection */}
                            <div className="input-group">
                                <input
                                    type="number"
                                    name="weightValue"
                                    placeholder="⚖️ Weight"
                                    value={formData.weightValue}
                                    onChange={handleChange}
                                    required
                                />
                                <select
                                    name="weightUnit"
                                    value={formData.weightUnit}
                                    onChange={handleChange}
                                    className="unit-select"
                                >
                                    <option value="kg">kg</option>
                                    <option value="lbs">lbs</option>
                                </select>
                            </div>

                            <input
                                type="number"
                                name="caloriesIntake"
                                placeholder="🍎 Daily Calorie Intake (e.g., 2000)"
                                value={formData.caloriesIntake}
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
                            <button type="submit" className="animated-btn" disabled={loadingPredictions}>
                                {loadingPredictions ? 'Processing...' : '✅ Get Exercise Plan'}
                            </button>
                            {predictionError && <p className="error-message">{predictionError}</p>}
                        </form>
                    </>
                ) : ( // After initial submission
                    <div className={`report-wrapper ${dietPlan ? 'with-diet-plan' : ''}`}>
                        {/* Exercise Report Section */}
                        <div className="recommendation-report fade-in-table">
                            <h2>Daily Exercise Recommendation Report</h2>
                            {exercisePlan ? (
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
                                            <td>{exercisePlan.exercise_type}</td>
                                            <td>{exercisePlan.intensity_level}</td>
                                            <td>{exercisePlan.frequency_per_week} times/week</td>
                                            <td>{exercisePlan.duration_minutes} mins/session</td>
                                            <td>{exercisePlan.estimated_calorie_burn} kcal/session</td>
                                        </tr>
                                    </tbody>
                                </table>
                            ) : (
                                <p>No exercise plan available.</p>
                            )}

                            <div className="report-buttons">
                                {/* Only show "Get Diet Plan" if it hasn't been generated yet */}
                                {!dietPlan && (
                                    <button
                                        className="animated-btn"
                                        onClick={() => setShowDietInputForm(true)}
                                    >
                                        Get Diet Plan
                                    </button>
                                )}
                                {/* Always allow downloading the combined report after exercise plan is ready */}
                                <button className="animated-btn" onClick={handleDownloadReport}>
                                    Download Overall Fitness Report (PDF)
                                </button>
                            </div>
                        </div>

                        {/* Optional Diet Input Form */}
                        {showDietInputForm && !dietPlan && (
                            <div className="diet-input-form slide-in">
                                <h2>Provide More Details for Diet Plan</h2>
                                <form onSubmit={handleDietPrediction}>
                                    <textarea
                                        name="medicalConditions"
                                        placeholder="🩺 Medical Conditions (e.g., Diabetes, Hypertension)"
                                        value={dietAdditionalDetails.medicalConditions}
                                        onChange={handleDietDetailsChange}
                                        rows="3"
                                    />
                                    <textarea
                                        name="dietaryRestrictions"
                                        placeholder="🚫 Dietary Restrictions (e.g., Vegetarian, Vegan, Allergies)"
                                        value={dietAdditionalDetails.dietaryRestrictions}
                                        onChange={handleDietDetailsChange}
                                        rows="3"
                                    />
                                    <textarea
                                        name="foodPreferences"
                                        placeholder="😋 Food Preferences/Dislikes (e.g., love chicken, hate broccoli)"
                                        value={dietAdditionalDetails.foodPreferences}
                                        onChange={handleDietDetailsChange}
                                        rows="3"
                                    />
                                    <button type="submit" className="animated-btn" disabled={loadingDietPlan}>
                                        {loadingDietPlan ? 'Generating Diet Plan...' : 'Generate Diet Plan'}
                                    </button>
                                    {dietPredictionError && <p className="error-message">{dietPredictionError}</p>}
                                </form>
                            </div>
                        )}

                        {/* Diet Plan Display */}
                        {dietPlan && (
                            <div className="recommendation-report diet-plan slide-in">
                                <h2>VitaFit Suggested Diet Plan</h2>
                                {!dietPlan.error && (
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
                                                <td>{dietPlan.recommended_calories} kcal</td>
                                                <td>{dietPlan.protein_grams_per_day} g</td>
                                                <td>{dietPlan.carbs_grams_per_day} g</td>
                                                <td>{dietPlan.fats_grams_per_day} g</td>
                                            </tr>
                                        </tbody>
                                    </table>
                                )}
                                {dietPlan.error && <p className="error-message">{dietPlan.error}</p>}
                                {dietPlan.message && <p className="info-message">{dietPlan.message}</p>} {/* Display model not available message */}

                                <div className="diet-final-section">
                                    <p>
                                        Your complete fitness report including both exercise and diet recommendations
                                        can be downloaded below.
                                    </p>
                                    {/* The download button is already above, just ensure it's visible */}
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