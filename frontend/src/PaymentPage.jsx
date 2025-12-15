import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import api from './api';

function PaymentPage() {
    const location = useLocation();
    const navigate = useNavigate();
    
    // Lấy thông tin từ trang trước
    const { order_id } = location.state || {};
    
    // State lưu giá tiền (Ưu tiên lấy từ state, nếu không có thì để null)
    const [totalPrice, setTotalPrice] = useState(location.state?.total_price || null);
    
    const [savedCards, setSavedCards] = useState([]);
    const [selectedCardId, setSelectedCardId] = useState('new'); 
    const [processing, setProcessing] = useState(false);
    const [newCard, setNewCard] = useState({ bank_name: '', card_number: '', card_holder: '', expiry_date: '' });

    useEffect(() => {
        // Nếu không có ID thì quay về shop
        if (!order_id) { navigate('/shop'); return; }
        
        fetchCards();
        
        // --- LOGIC QUAN TRỌNG ĐỂ SỬA LỖI NAN ---
        // Nếu giá tiền chưa có hoặc bị NaN (do F5), gọi API lấy lại ngay
        if (!totalPrice || isNaN(totalPrice)) {
            fetchOrderDetail();
        }
    }, [order_id]);

    const fetchOrderDetail = async () => {
        try {
            // Gọi API Backend để lấy giá chuẩn
            const res = await api.get(`/orders/${order_id}`);
            if (res.data) {
                console.log("Đã cập nhật lại giá tiền từ Server:", res.data.total_price);
                setTotalPrice(res.data.total_price);
            }
        } catch (err) {
            console.error("Lỗi lấy thông tin đơn hàng:", err);
            toast.error("Không thể tải thông tin đơn hàng!");
        }
    };

    const fetchCards = async () => {
        const token = localStorage.getItem('access_token');
        try {
            const res = await api.get('/payment-methods', { headers: { Authorization: `Bearer ${token}` } });
            setSavedCards(res.data || []);
            if (res.data && res.data.length > 0) setSelectedCardId(res.data[0].id);
        } catch (err) { 
            console.log("Chưa có thẻ đã lưu"); 
        }
    };

    const handleConfirmPayment = async () => {
        // CHẶN THANH TOÁN NẾU GIÁ VẪN LÀ NAN
        if (!totalPrice || isNaN(totalPrice)) {
            toast.error("Đang tải giá tiền, vui lòng đợi...");
            fetchOrderDetail(); // Thử load lại lần nữa
            return;
        }

        setProcessing(true);
        const token = localStorage.getItem('access_token');
        try {
            if (selectedCardId === 'new') {
                if (newCard.card_number && newCard.card_holder) {
                     try {
                        await api.post('/payment-methods', newCard, { headers: { Authorization: `Bearer ${token}` } });
                     } catch(e) {}
                }
            }
            
            await new Promise(r => setTimeout(r, 1500));
            
            // Gửi request thanh toán với số tiền chuẩn
            await api.post('/pay', { 
                order_id: order_id, 
                amount: totalPrice // Đảm bảo số này không bị NaN
            });
            
            toast.success("Thanh toán thành công! 💸");
            try { await api.delete('/cart'); } catch(e) {}
            navigate('/history');
            
        } catch (err) { 
            console.error(err); 
            // Hiển thị lỗi rõ ràng từ backend
            toast.error("Lỗi: " + (err.response?.data?.detail || "Thanh toán thất bại")); 
        } finally { 
            setProcessing(false); 
        }
    };

    const formatMoney = (a) => {
        if (a === null || a === undefined || isNaN(a)) return "Đang tính...";
        return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(a);
    };

    return (
        <div className="container" style={{maxWidth: '600px', marginTop: '40px', position: 'relative'}}>
            {/* BRANDING */}
            <div style={{position:'absolute', top: '-40px', right: '0', color: '#ff6347', fontWeight: '900', fontFamily: 'Arial'}}>FOOD ORDER</div>

            <h2 style={{textAlign: 'center', marginBottom: '30px'}}>💳 Cổng Thanh Toán</h2>
            <div style={{background: '#f8f9fa', padding: '20px', borderRadius: '8px', marginBottom: '20px', textAlign: 'center'}}>
                <p>Thanh toán cho đơn hàng <b>#{order_id}</b></p>
                
                {/* HIỂN THỊ GIÁ TIỀN */}
                <h1 style={{color: '#d32f2f', margin: '10px 0'}}>{formatMoney(totalPrice)}</h1>
            </div>

            <div className="payment-methods">
                <h3 style={{marginBottom: '15px'}}>Chọn phương thức:</h3>
                {savedCards.map(card => (
                    <div key={card.id} onClick={() => setSelectedCardId(card.id)} style={{ border: selectedCardId === card.id ? '2px solid #007bff' : '1px solid #ddd', padding: '15px', borderRadius: '8px', marginBottom: '10px', cursor: 'pointer', background: selectedCardId === card.id ? '#e7f1ff' : 'white', display: 'flex', alignItems: 'center' }}>
                        <input type="radio" checked={selectedCardId === card.id} onChange={() => setSelectedCardId(card.id)} style={{marginRight: '15px', transform: 'scale(1.5)'}} />
                        <div><div style={{fontWeight: 'bold'}}>🏦 {card.bank_name}</div><div>**** **** **** {card.card_number.slice(-4)}</div><small>{card.card_holder}</small></div>
                    </div>
                ))}

                <div onClick={() => setSelectedCardId('new')} style={{ border: selectedCardId === 'new' ? '2px solid #007bff' : '1px solid #ddd', padding: '15px', borderRadius: '8px', marginBottom: '10px', cursor: 'pointer', background: selectedCardId === 'new' ? '#fff' : '#f9f9f9' }}>
                    <div style={{display: 'flex', alignItems: 'center', marginBottom: selectedCardId === 'new' ? '15px' : '0'}}>
                        <input type="radio" checked={selectedCardId === 'new'} onChange={() => setSelectedCardId('new')} style={{marginRight: '15px', transform: 'scale(1.5)'}} />
                        <b>➕ Thêm thẻ / Tài khoản mới</b>
                    </div>
                    {selectedCardId === 'new' && (
                        <div style={{marginLeft: '30px'}}>
                            <input placeholder="Ngân hàng (VD: MBBank)" value={newCard.bank_name} onChange={e=>setNewCard({...newCard, bank_name: e.target.value})} style={{width: '100%', padding: '10px', marginBottom: '10px'}} />
                            <input placeholder="Số thẻ" value={newCard.card_number} onChange={e=>setNewCard({...newCard, card_number: e.target.value})} style={{width: '100%', padding: '10px', marginBottom: '10px'}} />
                            <div style={{display: 'flex', gap: '10px'}}>
                                <input placeholder="Chủ thẻ" value={newCard.card_holder} onChange={e=>setNewCard({...newCard, card_holder: e.target.value.toUpperCase()})} style={{flex: 2, padding: '10px'}} />
                                <input placeholder="MM/YY" value={newCard.expiry_date} onChange={e=>setNewCard({...newCard, expiry_date: e.target.value})} style={{flex: 1, padding: '10px'}} />
                            </div>
                        </div>
                    )}
                </div>
            </div>

            <button onClick={handleConfirmPayment} disabled={processing} style={{ width: '100%', padding: '15px', fontSize: '1.2rem', fontWeight: 'bold', background: processing ? '#6c757d' : '#28a745', color: 'white', border: 'none', borderRadius: '8px', marginTop: '20px', cursor: processing ? 'not-allowed' : 'pointer' }}>
                {processing ? "⏳ Đang kết nối..." : "THANH TOÁN NGAY"}
            </button>
        </div>
    );
}
export default PaymentPage;