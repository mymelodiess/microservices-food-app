import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { FaArrowLeft, FaBoxOpen } from "react-icons/fa"; // Thêm icon hộp rỗng
import api from './api';

const API_URL = "http://localhost:8000";

function OrderHistory() {
    const [orders, setOrders] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showReviewModal, setShowReviewModal] = useState(false);
    const [selectedOrder, setSelectedOrder] = useState(null);
    const [reviewData, setReviewData] = useState({ rating: 5, comment: '' });
    const navigate = useNavigate();

    useEffect(() => {
        fetchOrders();
        // Polling cập nhật trạng thái đơn hàng mỗi 5 giây
        const interval = setInterval(() => fetchOrders(true), 5000);
        return () => clearInterval(interval);
    }, []);

    const fetchOrders = async (isBackground = false) => {
        // Lấy User ID (Nếu chưa đăng nhập thì mặc định là 1 để test)
        const userId = localStorage.getItem('user_id') || 1;
        
        try {
            if(!isBackground) setLoading(true);
            
            // --- SỬA LỖI TẠI ĐÂY ---
            // Code cũ: '/orders/my-orders' (Sai) -> Code mới: '/orders' (Đúng)
            const res = await api.get('/orders', { params: { user_id: userId } });
            setOrders(res.data);
        } catch (err) { 
            console.error("Lỗi tải lịch sử:", err);
            // Không toast lỗi nếu đang chạy ngầm để tránh spam
            if (!isBackground) toast.error("Không tải được lịch sử đơn hàng");
        } 
        finally { if(!isBackground) setLoading(false); }
    };

    const handleCancelOrder = async (orderId) => {
        if (!window.confirm("Hủy đơn này?")) return;
        try {
            // Gọi API hủy (Lưu ý: Backend phải hỗ trợ PUT status)
            // Nếu backend chưa có api này thì sẽ lỗi 405/404, tạm thời cứ để logic ở đây
            await api.put(`/orders/${orderId}/status`, null, { params: { status: 'CANCELLED' } });
            toast.success("Đã hủy đơn");
            fetchOrders();
        } catch (err) { toast.error("Lỗi hủy đơn (Backend chưa hỗ trợ)"); }
    };

    const openReviewModal = (order) => {
        if (!order.items || order.items.length === 0) { toast.error("Không tìm thấy thông tin món ăn!"); return; }
        setSelectedOrder(order); setShowReviewModal(true); setReviewData({ rating: 5, comment: '' });
    };

    const submitReview = async () => {
        if (!selectedOrder) return;
        const token = localStorage.getItem('access_token');
        try {
            const payload = {
                order_id: selectedOrder.id,
                rating_general: reviewData.rating,
                comment: reviewData.comment,
                items: selectedOrder.items.map(item => ({ food_id: item.food_id, score: reviewData.rating }))
            };
            await api.post('/reviews', payload, { headers: { Authorization: `Bearer ${token}` } });
            toast.success("Đánh giá thành công! ⭐"); setShowReviewModal(false);
        } catch (err) { console.error(err); toast.error("Chức năng đánh giá chưa khả dụng"); }
    };

    const renderStatus = (status) => {
        const styles = { 
            'PENDING': {color:'orange', label:'⏳ Chờ xác nhận'}, 
            'PENDING_SHIPPING': {color:'#17a2b8', label:'📦 Chờ giao hàng'},
            'PAID': {color:'green', label:'✅ Đã thanh toán'}, 
            'SHIPPING': {color:'blue', label:'🚚 Đang giao'}, 
            'COMPLETED': {color:'gray', label:'🎉 Hoàn tất'}, 
            'CANCELLED': {color:'red', label:'❌ Đã hủy'} 
        };
        const s = styles[status] || { color: 'black', label: status };
        return <span style={{ color: s.color, fontWeight: 'bold', background:'#fff', padding:'2px 8px', borderRadius:'4px', border:`1px solid ${s.color}` }}>{s.label}</span>;
    };
    
    const formatMoney = (a) => new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(a);
    const formatDate = (d) => new Date(d).toLocaleString('vi-VN');

    return (
        <div className="container" style={{maxWidth: '900px', margin:'20px auto', padding:'0 15px'}}>
             {/* HEADER */}
            <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'20px', borderBottom: '1px solid #eee', paddingBottom: '15px'}}>
                <div style={{display:'flex', alignItems:'center', gap:'15px'}}>
                    <button onClick={() => navigate('/shop')} className="icon-btn" title="Quay lại mua sắm" style={{background:'#f0f0f0', border:'none', width:'40px', height:'40px', borderRadius:'50%', cursor:'pointer'}}>
                        <FaArrowLeft size={18} color="#555" />
                    </button>
                    <h2 style={{margin:0, color:'#333'}}>📜 Lịch sử đơn hàng</h2>
                </div>
                <h2 style={{color: '#ff6347', fontWeight: '900', fontFamily: 'Arial', margin:0}}>FOOD ORDER</h2>
            </div>

            {/* DANH SÁCH ĐƠN HÀNG */}
            {loading ? (
                <p style={{textAlign:'center', color:'#999'}}>Đang tải dữ liệu...</p>
            ) : orders.length === 0 ? (
                // EMPTY STATE (Hiển thị khi không có đơn)
                <div style={{textAlign:'center', padding:'50px', background:'#f9f9f9', borderRadius:'10px'}}>
                    <FaBoxOpen size={50} color="#ccc" style={{marginBottom:'15px'}}/>
                    <h3 style={{color:'#666', margin:'0 0 10px'}}>Bạn chưa có đơn hàng nào</h3>
                    <button onClick={() => navigate('/shop')} style={{marginTop:'15px', padding:'10px 25px', background:'#ff6347', color:'white', border:'none', borderRadius:'5px', cursor:'pointer', fontWeight:'bold'}}>
                        Đặt món ngay
                    </button>
                </div>
            ) : (
                <div className="order-list">
                    {orders.map(order => (
                        <div key={order.id} style={{border:'1px solid #e0e0e0', padding:'20px', marginBottom:'20px', borderRadius:'10px', background: 'white', boxShadow:'0 2px 8px rgba(0,0,0,0.05)'}}>
                            {/* Order Header */}
                            <div style={{display:'flex', justifyContent:'space-between', borderBottom:'1px dashed #eee', paddingBottom:'15px', marginBottom:'15px'}}>
                                <div>
                                    <strong style={{fontSize:'1.1rem', color:'#333'}}>Đơn hàng #{order.id}</strong> 
                                    <span style={{color:'#888', fontSize:'0.9rem', marginLeft:'10px'}}>• {formatDate(order.created_at)}</span>
                                </div>
                                <div>{renderStatus(order.status)}</div>
                            </div>

                            {/* Order Items */}
                            <div style={{background: '#fafafa', padding: '15px', borderRadius: '8px', marginBottom: '15px'}}>
                                {order.items?.map((item, idx) => (
                                    <div key={idx} style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.95rem', marginBottom: '10px', lastChild: {marginBottom:0}}}>
                                        <div style={{display: 'flex', alignItems: 'center'}}>
                                            {item.image_url ? ( 
                                                <img src={`${API_URL}${item.image_url}`} style={{width: '40px', height: '40px', objectFit: 'cover', borderRadius: '6px', marginRight: '12px', border:'1px solid #ddd'}} alt="" /> 
                                            ) : ( 
                                                <div style={{width:'40px', height:'40px', background:'#eee', borderRadius:'6px', marginRight:'12px', display:'flex', alignItems:'center', justifyContent:'center'}}>🍖</div> 
                                            )}
                                            <div>
                                                <div style={{fontWeight:'600', color:'#444'}}>{item.food_name}</div>
                                                <div style={{fontSize:'0.85rem', color:'#888'}}>x{item.quantity}</div>
                                            </div>
                                        </div>
                                        <span style={{color: '#555', fontWeight:'500'}}>{formatMoney(item.price)}</span>
                                    </div>
                                ))}
                            </div>

                            {/* Order Footer */}
                            <div style={{display:'flex', justifyContent:'space-between', alignItems:'flex-end'}}>
                                <div>
                                    <div style={{fontSize: '0.9rem', color:'#666', marginBottom:'5px'}}>📍 Giao đến: {order.delivery_address || 'Tại quán'}</div>
                                    <div style={{fontSize: '0.9rem', color:'#666'}}>👤 Người nhận: {order.customer_name}</div>
                                </div>
                                <div style={{textAlign:'right'}}>
                                    <div style={{fontSize:'0.9rem', color:'#888', marginBottom:'5px'}}>Tổng tiền</div>
                                    <div style={{color:'#d32f2f', fontWeight:'bold', fontSize: '1.4rem'}}>{formatMoney(order.total_price)}</div>
                                </div>
                            </div>

                            {/* Actions */}
                            <div style={{marginTop:'15px', paddingTop:'15px', borderTop:'1px solid #eee', display:'flex', justifyContent:'flex-end', gap:'10px'}}>
                                {['PENDING','PENDING_PAYMENT'].includes(order.status) && (
                                    <button onClick={()=>handleCancelOrder(order.id)} style={{color:'#dc3545', border:'1px solid #dc3545', background:'white', padding: '8px 15px', borderRadius:'4px', cursor: 'pointer', fontWeight:'600'}}>
                                        Hủy đơn hàng
                                    </button>
                                )}
                                {order.status === 'COMPLETED' && (
                                    <button onClick={()=>openReviewModal(order)} style={{background:'#f6c23e', color:'white', border:'none', padding:'8px 20px', borderRadius:'4px', cursor: 'pointer', fontWeight: 'bold'}}>
                                        ⭐ Đánh giá
                                    </button>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Review Modal */}
            {showReviewModal && (
                <div className="modal-overlay" onClick={()=>setShowReviewModal(false)}>
                    <div className="modal-content" onClick={e=>e.stopPropagation()}>
                        <h3 style={{textAlign:'center'}}>Đánh giá đơn #{selectedOrder?.id}</h3>
                        <div style={{textAlign:'center', margin:'20px 0', fontSize:'2rem', color:'#f6c23e', cursor:'pointer'}}>
                            {[1,2,3,4,5].map(s=>(<span key={s} onClick={()=>setReviewData({...reviewData, rating:s})}>{s<=reviewData.rating?'★':'☆'}</span>))}
                        </div>
                        <textarea style={{width:'100%', padding:'10px', height:'100px', borderRadius:'5px', border:'1px solid #ccc'}} placeholder="Món ăn thế nào? Hãy chia sẻ cảm nhận..." value={reviewData.comment} onChange={e=>setReviewData({...reviewData, comment:e.target.value})} />
                        <div style={{display:'flex', gap:'10px', marginTop:'20px'}}>
                            <button onClick={()=>setShowReviewModal(false)} style={{flex:1, padding:'10px', cursor:'pointer'}}>Đóng</button>
                            <button onClick={submitReview} style={{flex:1, background:'#28a745', color:'white', border:'none', borderRadius:'4px', cursor:'pointer', fontWeight:'bold'}}>Gửi đánh giá</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
export default OrderHistory;