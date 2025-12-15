import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { toast } from 'react-toastify';
import api from './api';

function Login() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleLogin = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            const res = await api.post('/login', { email, password });
            
            // Log ra để kiểm tra xem backend trả về gì
            console.log("Login Response:", res.data);

            const { access_token, role, branch_id, id } = res.data;

            // Lưu dữ liệu quan trọng
            localStorage.setItem('access_token', access_token);
            localStorage.setItem('role', role);
            localStorage.setItem('user_id', id);
            
            // Xử lý logic Branch ID kỹ càng hơn
            if (branch_id) {
                localStorage.setItem('branch_id', branch_id);
            } else {
                // Nếu backend trả về user object lồng nhau (tùy cấu trúc backend cũ của bạn)
                if (res.data.user && res.data.user.branch_id) {
                    localStorage.setItem('branch_id', res.data.user.branch_id);
                }
            }

            toast.success("Đăng nhập thành công!");

            if (role === 'seller') {
                navigate('/seller-dashboard');
            } else {
                navigate('/shop');
            }

        } catch (err) {
            console.error(err);
            toast.error("Đăng nhập thất bại! Kiểm tra lại Email/Pass hoặc Server.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="container" style={{maxWidth:'500px', marginTop:'80px', textAlign:'center'}}>
            <h1 style={{color: '#ff6347', fontSize:'40px', fontWeight:'900'}}>FOOD ORDER</h1>
            <h2 style={{margin:'20px 0'}}>Đăng nhập</h2>
            <form onSubmit={handleLogin} className="auth-form" style={{display:'flex', flexDirection:'column', gap:'15px'}}>
                <input type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} required style={{padding:'15px'}} />
                <input type="password" placeholder="Mật khẩu" value={password} onChange={e => setPassword(e.target.value)} required style={{padding:'15px'}} />
                <button type="submit" disabled={loading} style={{padding:'15px', background:'#2c3e50', color:'white', fontSize:'18px'}}>
                    {loading ? "Đang kết nối..." : "Đăng nhập ngay"}
                </button>
            </form>
            <p style={{marginTop:'20px'}}>Chưa có tài khoản? <Link to="/register" style={{fontWeight:'bold', color:'#ff6347'}}>Đăng ký ngay</Link></p>
        </div>
    );
}
export default Login;