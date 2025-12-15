import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { FaArrowLeft, FaMapMarkerAlt, FaFileInvoiceDollar, FaUser, FaPhone, FaStickyNote } from "react-icons/fa"; 
import api from './api';

const API_URL = "http://localhost:8000";

function Checkout() {
    const location = useLocation();
    const navigate = useNavigate();
    
    // LẤY DỮ LIỆU TỪ GIỎ HÀNG CHUYỂN QUA
    // final_price: Là con số 70.000đ bạn thấy trên màn hình
    const { items, coupon, final_price, branch_id } = location.state || {};

    const [customerInfo, setCustomerInfo] = useState({ name: '', phone: '', address: '', note: '' });
    const [branchName, setBranchName] = useState('Đang tải...');
    const [savedAddresses, setSavedAddresses] = useState([]); 
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!items || items.length === 0) { navigate('/shop'); return; }
        if (branch_id) fetchBranchInfo();
        fetchSavedAddresses(); 
    }, [items, branch_id, navigate]);

    const fetchSavedAddresses = async () => {
        const token = localStorage.getItem('access_token');
        if (!token) return;
        try {
            const res = await api.get('/users/addresses', { headers: { Authorization: `Bearer ${token}` } });
            setSavedAddresses(res.data);
        } catch (err) { console.error(err); }
    };

    const handleSelectAddress = (e) => {
        const addrId = e.target.value;
        if (!addrId) return;
        const selected = savedAddresses.find(a => a.id == addrId);
        if (selected) {
            setCustomerInfo(prev => ({ 
                ...prev, 
                name: selected.name, 
                phone: selected.phone, 
                address: selected.address 
            }));
            toast.info(`Đã điền: ${selected.title}`);
        }
    };

    const fetchBranchInfo = async () => {
        try {
            const res = await api.get(`/branches/${branch_id}`);
            setBranchName(res.data.name);
        } catch (err) { setBranchName(`Chi nhánh #${branch_id}`); }
    };

    const handleChange = (e) => setCustomerInfo({...customerInfo, [e.target.name]: e.target.value});

    const handleConfirmOrder = async () => {
        if (!customerInfo.address || !customerInfo.phone || !customerInfo.name) {
            toast.warning("Thiếu thông tin giao hàng! ✍️");
            return;
        }
        setLoading(true);
        const userId = localStorage.getItem('user_id');

        try {
            const orderPayload = {
                user_id: userId ? parseInt(userId) : 1, // Mặc định 1 nếu chưa login
                branch_id: branch_id,
                items: items.map(item => ({ 
                    food_id: item.food_id, 
                    quantity: item.quantity,
                    price: item.price, // Gửi kèm giá để backend lưu
                    food_name: item.name 
                })),
                coupon_code: coupon ? coupon.code : null,
                customer_name: customerInfo.name,
                customer_phone: customerInfo.phone,
                delivery_address: customerInfo.address,
                note: customerInfo.note
            };
            
            // Gọi API tạo đơn
            const orderRes = await api.post('/checkout', orderPayload);
            const { order_id } = orderRes.data; // Chỉ cần lấy ID đơn hàng mới

            toast.info("Đang chuyển sang thanh toán...");
            
            // --- SỬA CHỖ NÀY: TRUYỀN THẲNG GIÁ TIỀN CŨ SANG ---
            navigate('/payment', { 
                state: { 
                    order_id: order_id, 
                    total_price: final_price // <--- Lấy biến final_price có sẵn (70000), không chờ backend
                } 
            });

        } catch (err) {
            console.error(err);
            toast.error("Lỗi đặt hàng: " + (err.response?.data?.detail || "Thử lại sau"));
        } finally {
            setLoading(false);
        }
    };

    const formatMoney = (a) => new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(a);
    if (!items) return null;

    return (
        <div style={{
            width: '98vw', margin: '10px auto', background: 'white',
            borderRadius: '8px', boxShadow: '0 2px 10px rgba(0,0,0,0.05)',
            padding: '20px', boxSizing: 'border-box', minHeight: '90vh'
        }}>
             {/* Header */}
             <div style={{display:'flex', alignItems:'center', borderBottom:'1px solid #eee', paddingBottom:'10px', marginBottom:'20px'}}>
                <button onClick={() => navigate('/cart')} className="icon-btn" title="Quay lại" style={{width:'40px', height:'40px'}}><FaArrowLeft /></button>
                <h2 style={{marginLeft:'15px', textTransform:'uppercase', color:'#ff6347', fontSize:'1.5rem', margin: 0}}>Xác nhận đặt hàng</h2>
            </div>

            {/* Layout 2 Cột */}
            <div style={{display: 'flex', gap: '30px', alignItems: 'flex-start'}}>
                
                {/* CỘT TRÁI: FORM */}
                <div style={{flex: '65%'}}>
                    <h3 style={{display:'flex', alignItems:'center', gap:'10px', marginTop:0, marginBottom:'15px', color:'#333'}}>
                        <FaMapMarkerAlt color="#ff6347"/> Thông tin giao hàng
                    </h3>
                    
                    {savedAddresses.length > 0 && (
                        <div style={{marginBottom: '15px', display:'flex', alignItems:'center', gap:'10px', background: '#f0f8ff', padding: '10px', borderRadius: '6px'}}>
                            <label style={{whiteSpace:'nowrap', fontWeight:'bold', color:'#007bff'}}>⚡ Chọn nhanh:</label>
                            <select onChange={handleSelectAddress} style={{flex:1, padding: '8px', borderRadius:'4px', border:'1px solid #ccc'}}>
                                <option value="">-- Sổ địa chỉ --</option>
                                {savedAddresses.map(addr => (
                                    <option key={addr.id} value={addr.id}>{addr.title} - {addr.name}</option>
                                ))}
                            </select>
                        </div>
                    )}

                    <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:'15px'}}>
                        <div>
                            <label style={{fontSize:'0.9rem', fontWeight:'600', color:'#555', display:'block', marginBottom:'5px'}}><FaUser/> Người nhận</label>
                            <input name="name" value={customerInfo.name} onChange={handleChange} placeholder="Họ tên" style={{width:'100%', padding:'10px', border:'1px solid #ddd', borderRadius:'4px'}} />
                        </div>
                        <div>
                            <label style={{fontSize:'0.9rem', fontWeight:'600', color:'#555', display:'block', marginBottom:'5px'}}><FaPhone/> Số điện thoại</label>
                            <input name="phone" value={customerInfo.phone} onChange={handleChange} placeholder="09xxxx" style={{width:'100%', padding:'10px', border:'1px solid #ddd', borderRadius:'4px'}} />
                        </div>
                    </div>
                    
                    <div style={{marginTop:'15px'}}>
                        <label style={{fontSize:'0.9rem', fontWeight:'600', color:'#555', display:'block', marginBottom:'5px'}}><FaMapMarkerAlt/> Địa chỉ chi tiết</label>
                        <textarea name="address" value={customerInfo.address} onChange={handleChange} placeholder="Số nhà, đường, phường/xã..." style={{width:'100%', padding:'10px', border:'1px solid #ddd', borderRadius:'4px', height:'60px', fontFamily:'inherit'}} />
                    </div>

                    <div style={{marginTop:'15px'}}>
                        <label style={{fontSize:'0.9rem', fontWeight:'600', color:'#555', display:'block', marginBottom:'5px'}}><FaStickyNote/> Ghi chú (Tùy chọn)</label>
                        <input name="note" value={customerInfo.note} onChange={handleChange} placeholder="VD: Ít cay, nhiều nước lèo..." style={{width:'100%', padding:'10px', border:'1px solid #ddd', borderRadius:'4px'}} />
                    </div>
                </div>

                {/* CỘT PHẢI: TÓM TẮT (Sticky) */}
                <div style={{
                    flex: '35%', background: '#fcfcfc', padding: '20px', 
                    borderRadius: '8px', border: '1px solid #eee',
                    boxShadow: '0 4px 15px rgba(0,0,0,0.03)', position: 'sticky', top: '10px'
                }}>
                    <h3 style={{marginTop:0, borderBottom:'1px dashed #ccc', paddingBottom:'10px', display:'flex', alignItems:'center', gap:'10px', fontSize:'1.1rem'}}>
                         <FaFileInvoiceDollar color="#ff6347"/> Đơn hàng từ: <span style={{color: '#007bff'}}>{branchName}</span>
                    </h3>
                    
                    <div style={{maxHeight:'40vh', overflowY:'auto', paddingRight:'5px', marginBottom:'15px'}}>
                        {items.map(item => (
                            <div key={item.food_id} style={{display:'flex', alignItems: 'center', justifyContent:'space-between', marginBottom:'12px', borderBottom:'1px solid #f0f0f0', paddingBottom:'8px'}}>
                                <div style={{display:'flex', alignItems: 'center', gap: '10px'}}>
                                    {item.image_url ? 
                                        <img src={`${API_URL}${item.image_url}`} style={{width:'40px', height:'40px', objectFit:'cover', borderRadius:'4px', border:'1px solid #ddd'}} alt="" /> 
                                        : <div style={{width:'40px', height:'40px', background:'#eee', borderRadius:'4px'}}></div>
                                    }
                                    <div>
                                        <div style={{fontWeight:'bold', fontSize:'0.9rem'}}>{item.name}</div>
                                        <div style={{fontSize:'0.8rem', color:'#666'}}>x{item.quantity}</div>
                                    </div>
                                </div>
                                <span style={{fontWeight:'600', fontSize:'0.95rem'}}>{formatMoney(item.price*item.quantity)}</span>
                            </div>
                        ))}
                    </div>
                    
                    {coupon && (
                        <div style={{display:'flex', justifyContent:'space-between', color:'green', background:'#e8f5e9', padding:'8px', borderRadius:'4px', marginBottom:'10px', fontWeight:'600', fontSize:'0.9rem'}}>
                            <span>Mã giảm ({coupon.code}):</span>
                            <span>-{coupon.discount_percent}%</span>
                        </div>
                    )}
                    
                    <div style={{display:'flex', justifyContent:'space-between', fontSize:'1.4rem', fontWeight:'800', marginTop:'10px', color:'#333', borderTop:'2px solid #333', paddingTop:'15px'}}>
                        <span>Tổng tiền:</span>
                        <span style={{color:'#ff6347'}}>{formatMoney(final_price)}</span>
                    </div>
                    
                    <button onClick={handleConfirmOrder} disabled={loading} style={{
                        width: '100%', padding: '15px', background: 'linear-gradient(90deg, #ff6347, #ff4757)', color: 'white', 
                        border: 'none', borderRadius: '6px', fontWeight: 'bold', fontSize:'1.1rem', cursor:'pointer', marginTop: '20px',
                        boxShadow: '0 4px 10px rgba(255, 99, 71, 0.3)', transition: 'transform 0.2s'
                    }}>
                        {loading ? "Đang xử lý..." : "XÁC NHẬN ĐẶT HÀNG"}
                    </button>
                </div>
            </div>
        </div>
    );
}
export default Checkout;