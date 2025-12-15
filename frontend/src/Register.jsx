import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { FaEye, FaEyeSlash } from 'react-icons/fa'; // Import icon con mắt
import api from './api';
import './Register.css'; // Import file CSS vừa tạo

function Register() {
    const [formData, setFormData] = useState({
        name: '',
        phone: '',
        email: '',
        password: '',
        confirmPassword: ''
    });
    
    const [error, setError] = useState('');
    // State để quản lý việc hiện/ẩn mật khẩu
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);

    const navigate = useNavigate();

    // --- CÁC HÀM KIỂM TRA (VALIDATORS) ---
    const validators = {
        email: (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email),
        phone: (phone) => /(03|05|07|08|09|01[2|6|8|9])+([0-9]{8})\b|0\d{9}/.test(phone) && phone.length === 10,
        password: (pass) => /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/.test(pass)
    };

    const handleChange = (e) => {
        setFormData({...formData, [e.target.name]: e.target.value});
    };

    // Hàm toggle hiện/ẩn mật khẩu
    const togglePasswordVisibility = (field) => {
        if (field === 'password') {
            setShowPassword(!showPassword);
        } else if (field === 'confirmPassword') {
            setShowConfirmPassword(!showConfirmPassword);
        }
    };

    const handleRegister = async (e) => {
        e.preventDefault();
        setError('');

        // --- KIỂM TRA DỮ LIỆU ---
        if (!validators.email(formData.email)) return setError("Địa chỉ Email không hợp lệ!");
        if (!validators.phone(formData.phone)) return setError("Số điện thoại không hợp lệ (10 số, bắt đầu bằng 0)!");
        if (!validators.password(formData.password)) return setError("Mật khẩu quá yếu! Cần 8 ký tự, có hoa, thường, số & ký tự đặc biệt.");
        if (formData.password !== formData.confirmPassword) return setError("Mật khẩu xác nhận không khớp!");

        try {
            const payload = { 
                name: formData.name, phone: formData.phone, email: formData.email,
                password: formData.password, role: 'buyer', address: ""
            };
            await api.post('/register', payload);
            alert("Đăng ký thành công! Bạn có thể đăng nhập ngay.");
            navigate('/'); 

        } catch (err) {
            console.error("Lỗi đăng ký:", err);
            let errorMsg = "Đăng ký thất bại. Vui lòng thử lại.";
            if (err.response && err.response.data) {
                const detail = err.response.data.detail;
                errorMsg = Array.isArray(detail) ? detail[0].msg : (typeof detail === 'string' ? detail : JSON.stringify(detail));
            } else if (err.message) {
                errorMsg = err.message;
            }
            setError(errorMsg);
        }
    };

    return (
        <div className="register-container">
            <div className="register-box">
                <h2>Đăng ký Tài khoản</h2>
                
                <form onSubmit={handleRegister} className="auth-form">
                    {/* Họ tên */}
                    <div className="input-group">
                        <input 
                            className="input-field" name="name" placeholder="Họ và tên" required 
                            value={formData.name} onChange={handleChange} 
                        />
                    </div>

                    {/* Số điện thoại */}
                    <div className="input-group">
                        <input 
                            className="input-field" name="phone" placeholder="Số điện thoại" required 
                            value={formData.phone} onChange={handleChange} 
                        />
                    </div>

                    {/* Email */}
                    <div className="input-group">
                        <input 
                            className="input-field" name="email" type="email" placeholder="Email" required 
                            value={formData.email} onChange={handleChange} 
                        />
                    </div>

                    {/* Mật khẩu */}
                    <div className="input-group">
                        <div className="password-wrapper">
                            <input 
                                className="input-field" name="password" 
                                type={showPassword ? "text" : "password"} // Đổi type dựa trên state
                                placeholder="Mật khẩu" required 
                                value={formData.password} onChange={handleChange} 
                            />
                            {/* Nút con mắt */}
                            <button type="button" className="toggle-password-btn" onClick={() => togglePasswordVisibility('password')}>
                                {showPassword ? <FaEyeSlash /> : <FaEye />}
                            </button>
                        </div>
                        <small className="password-hint">
                            * Tối thiểu 8 ký tự, gồm: Hoa, thường, số & ký tự đặc biệt (@$!%*?&)
                        </small>
                    </div>

                    {/* Nhập lại mật khẩu */}
                    <div className="input-group">
                        <div className="password-wrapper">
                            <input 
                                className="input-field" name="confirmPassword" 
                                type={showConfirmPassword ? "text" : "password"} // Đổi type dựa trên state
                                placeholder="Nhập lại mật khẩu" required 
                                value={formData.confirmPassword} onChange={handleChange} 
                            />
                            {/* Nút con mắt */}
                            <button type="button" className="toggle-password-btn" onClick={() => togglePasswordVisibility('confirmPassword')}>
                                {showConfirmPassword ? <FaEyeSlash /> : <FaEye />}
                            </button>
                        </div>
                    </div>
                    
                    {/* Khu vực hiển thị lỗi */}
                    {error && (
                        <div className="error-message">
                            ⚠️ <span>{error}</span>
                        </div>
                    )}

                    <button type="submit" className="submit-btn">Đăng ký ngay</button>
                </form>

                <p className="login-link-text">
                    Đã có tài khoản? <Link to="/">Đăng nhập</Link>
                </p>
            </div>
        </div>
    );
}

export default Register;