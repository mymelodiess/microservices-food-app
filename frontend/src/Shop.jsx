import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { FaShoppingCart, FaHistory, FaUserCircle, FaSignOutAlt, FaSearch } from "react-icons/fa"; 
import api from './api';

// Đường dẫn gốc để hiển thị ảnh từ server (Nếu backend trả về đường dẫn tương đối)
const API_BASE_URL = "http://localhost:8000";

function Shop() {
    const [foods, setFoods] = useState([]);
    const [searchTerm, setSearchTerm] = useState(''); 
    const [selectedFood, setSelectedFood] = useState(null); 
    const [foodOptions, setFoodOptions] = useState([]);
    const navigate = useNavigate();

    useEffect(() => { 
        fetchFoods(); 
    }, []);

    const fetchFoods = async (query = '') => {
        try {
            // Gọi API thật: GET /foods/search?q=...
            const res = await api.get(`/foods/search?q=${query}`);
            setFoods(res.data || []);
        } catch (err) { 
            console.error(err);
            // Không dùng dữ liệu giả nữa, chỉ thông báo lỗi nếu cần
            // toast.error("Không tải được danh sách món ăn");
        }
    };

    const handleSearch = (e) => { e.preventDefault(); fetchFoods(searchTerm); };

    const handleViewOptions = async (foodName) => {
        try {
            // Gọi API thật: GET /foods/options?name=...
            const res = await api.get(`/foods/options?name=${foodName}`);
            setFoodOptions(res.data);
            setSelectedFood(foodName);
        } catch (err) { toast.error("Lỗi tải chi tiết món"); }
    };

    const handleAddToCart = async (option) => {
        try {
            // Gọi API thật: POST /cart
            await api.post('/cart', { food_id: option.food_id, branch_id: option.branch_id, quantity: 1 });
            toast.success(`Đã thêm vào giỏ! 🛒`);
            setSelectedFood(null);
        } catch (err) {
            if (err.response?.status === 409) {
                if(window.confirm("Giỏ hàng đang chứa món của quán khác! Bạn có muốn xóa giỏ cũ để thêm món này không?")) {
                    await api.delete('/cart');
                    await api.post('/cart', { food_id: option.food_id, branch_id: option.branch_id, quantity: 1 });
                    toast.success("Đã tạo giỏ mới!");
                    setSelectedFood(null);
                }
            } else { toast.error("Lỗi thêm vào giỏ"); }
        }
    };

    const handleLogout = () => { localStorage.clear(); navigate('/'); };
    const formatMoney = (a) => new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(a);

    return (
        <div className="shop-container">
            {/* Header */}
            <header className="shop-header">
                <h2 className="brand-title">FOOD ORDER</h2>
                <div className="header-actions">
                    <button onClick={() => navigate('/cart')} className="icon-btn" title="Giỏ hàng"><FaShoppingCart /></button>
                    <button onClick={() => navigate('/history')} className="icon-btn" title="Lịch sử"><FaHistory /></button>
                    <button onClick={() => navigate('/profile')} className="icon-btn" title="Hồ sơ"><FaUserCircle /></button>
                    <button onClick={handleLogout} className="icon-btn logout" title="Đăng xuất"><FaSignOutAlt /></button>
                </div>
            </header>

            {/* Thanh tìm kiếm */}
            <div className="search-bar">
                <form onSubmit={handleSearch}>
                    <input 
                        placeholder="Bạn muốn ăn gì hôm nay?..." 
                        value={searchTerm} 
                        onChange={(e) => setSearchTerm(e.target.value)} 
                    />
                    <button type="submit">Tìm kiếm</button>
                </form>
            </div>

            {/* Danh sách món ăn */}
            <div className="food-grid">
                {foods.length === 0 ? (
                    <p style={{width: '100%', textAlign: 'center', color: '#999'}}>Không tìm thấy món ăn nào.</p>
                ) : (
                    foods.map((food, index) => (
                        <div key={index} className="food-card" onClick={() => handleViewOptions(food.name)}>
                            {/* Hiển thị ảnh từ API thật */}
                            {food.image_url ? (
                                <img 
                                    src={food.image_url.startsWith('http') ? food.image_url : `${API_BASE_URL}${food.image_url}`} 
                                    alt={food.name} 
                                    onError={(e) => {e.target.src = "https://via.placeholder.com/300x200?text=No+Image"}} 
                                />
                            ) : (
                                <div style={{height:'180px', background:'#eee', display:'flex', alignItems:'center', justifyContent:'center'}}>🍖</div>
                            )}
                            
                            <h3>{food.name}</h3>
                            <div style={{padding:'0 15px', marginBottom:'5px', color:'#f6c23e', fontSize:'0.9rem'}}>
                                {food.avg_rating > 0 ? `★ ${food.avg_rating} (${food.review_count})` : "Chưa có đánh giá"}
                            </div>
                            <p className="price-range">
                                {formatMoney(food.min_price)} {food.min_price !== food.max_price && ` - ${formatMoney(food.max_price)}`}
                            </p>
                            <div style={{padding:'0 15px 15px', color:'#777', fontSize:'0.8rem'}}>
                                {food.branch_count} chi nhánh đang bán
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* Modal chọn quán (Giữ nguyên logic cũ) */}
            {selectedFood && (
                <div className="modal-overlay" onClick={() => setSelectedFood(null)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        <div style={{display:'flex', justifyContent:'space-between', marginBottom:'15px'}}>
                            <h3 style={{margin:0}}>Chọn quán: {selectedFood}</h3>
                            <button onClick={() => setSelectedFood(null)} style={{border:'none', background:'none', fontSize:'1.5rem', cursor:'pointer'}}>×</button>
                        </div>
                        
                        <div className="options-list">
                            {foodOptions.map((opt, idx) => (
                                <div key={idx} className="option-item" style={{display:'flex', justifyContent:'space-between', alignItems:'center', padding:'15px', borderBottom:'1px solid #eee'}}>
                                    <div style={{display:'flex', alignItems:'center'}}>
                                        {opt.image_url && <img src={opt.image_url.startsWith('http') ? opt.image_url : `${API_BASE_URL}${opt.image_url}`} style={{width:'50px', height:'50px', objectFit:'cover', borderRadius:'4px', marginRight:'10px'}} />}
                                        <div>
                                            <strong>{opt.branch_name}</strong><br/>
                                            <span style={{color:'red', fontWeight:'bold'}}>{formatMoney(opt.final_price)}</span>
                                        </div>
                                    </div>
                                    <button onClick={() => handleAddToCart(opt)} style={{background:'#ff6347', color:'white', padding:'8px 15px', borderRadius:'4px', border:'none', cursor:'pointer'}}>+ Thêm</button>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default Shop;