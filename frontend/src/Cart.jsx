import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { FaTrash, FaMinus, FaPlus, FaArrowLeft, FaShoppingBag } from "react-icons/fa"; 
import api from './api';

const API_URL = "http://localhost:8000";

function Cart() {
    const [cartItems, setCartItems] = useState([]);
    const [subTotal, setSubTotal] = useState(0);
    const [totalPrice, setTotalPrice] = useState(0);
    const [couponCode, setCouponCode] = useState('');
    const [appliedCoupon, setAppliedCoupon] = useState(null);
    const navigate = useNavigate();

    useEffect(() => { fetchCart(); }, []);

    useEffect(() => {
        if (appliedCoupon) {
            const discountAmount = (subTotal * appliedCoupon.discount_percent) / 100;
            setTotalPrice(subTotal - discountAmount);
        } else { setTotalPrice(subTotal); }
    }, [subTotal, appliedCoupon]);

    const fetchCart = async () => {
        try {
            const cartRes = await api.get('/cart');
            const items = cartRes.data;
            if (items.length === 0) { setCartItems([]); return; }

            const enrichedItems = await Promise.all(items.map(async (item) => {
                try {
                    const foodDetail = await api.get(`/foods/${item.food_id}`);
                    return {
                        ...item,
                        name: foodDetail.data.name,
                        price: foodDetail.data.price,
                        image_url: foodDetail.data.image_url
                    };
                } catch (e) { return { ...item, name: "Món đã xóa", price: 0 }; }
            }));

            setCartItems(enrichedItems);
            calculateSubTotal(enrichedItems);
        } catch (err) { console.error(err); }
    };

    const calculateSubTotal = (items) => {
        const total = items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
        setSubTotal(total);
    };

    const updateQuantity = async (foodId, newQty) => {
        if (newQty < 1) return;
        try {
            await api.put('/cart', { food_id: foodId, quantity: newQty });
            const updatedItems = cartItems.map(item => item.food_id === foodId ? { ...item, quantity: newQty } : item);
            setCartItems(updatedItems);
            calculateSubTotal(updatedItems);
        } catch (err) { toast.error("Lỗi cập nhật"); }
    };

    const removeItem = async (foodId) => {
        if(!window.confirm("Xóa món này khỏi giỏ?")) return;
        try {
            // Lưu ý: API hiện tại của bạn là xóa hết. Nếu backend hỗ trợ xóa 1 món thì gọi API đó.
            // Ở đây mình giả lập xóa trên giao diện trước
            const updatedItems = cartItems.filter(item => item.food_id !== foodId);
            setCartItems(updatedItems);
            calculateSubTotal(updatedItems);
            // Gọi API thực tế (nếu có): await api.delete(`/cart/${foodId}`); 
            // Hiện tại dùng tạm xóa all nếu backend chưa update:
            if(updatedItems.length === 0) await api.delete('/cart');
        } catch(err) { toast.error("Lỗi xóa món"); }
    };

    const clearCart = async () => {
        if (!window.confirm("Bạn chắc chắn muốn xóa hết giỏ hàng?")) return;
        try {
            await api.delete('/cart');
            setCartItems([]); setSubTotal(0); setAppliedCoupon(null);
            toast.info("Đã làm sạch giỏ hàng");
        } catch (err) { toast.error("Lỗi xóa giỏ"); }
    };

    const handleApplyCoupon = async () => {
        if (!couponCode) return;
        if (cartItems.length === 0) return toast.warning("Giỏ trống!");
        const currentBranchId = cartItems[0].branch_id;
        try {
            const res = await api.get('/coupons/verify', { params: { code: couponCode, branch_id: currentBranchId } });
            setAppliedCoupon(res.data);
            toast.success(`Mã giảm giá ${res.data.code} đã được áp dụng!`);
        } catch (err) { setAppliedCoupon(null); toast.error("Mã không hợp lệ hoặc hết hạn"); }
    };

    const handleCheckout = () => {
        if (cartItems.length === 0) return toast.warning("Giỏ trống!");
        navigate('/checkout', {
            state: { items: cartItems, coupon: appliedCoupon, final_price: totalPrice, branch_id: cartItems[0].branch_id }
        });
    };

    const formatMoney = (a) => new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(a);

    return (
        <div className="cart-container">
            {/* Header */}
            <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'30px'}}>
                <div style={{display:'flex', alignItems:'center', gap:'15px'}}>
                    <button onClick={() => navigate('/shop')} className="icon-btn" title="Quay lại"><FaArrowLeft /></button>
                    <h2 style={{margin:0, display:'flex', alignItems:'center', gap:'12px', color: '#333'}}>
                        <FaShoppingBag color="#ff6347"/> Giỏ hàng
                    </h2>
                </div>
                {cartItems.length > 0 && 
                    <button onClick={clearCart} style={{color:'#ff4757', background:'white', border:'1px solid #ff4757', padding:'8px 15px', borderRadius:'20px', cursor:'pointer', fontWeight:'600', transition:'0.2s'}}>
                        Xóa tất cả
                    </button>
                }
            </div>

            {cartItems.length === 0 ? (
                <div className="empty-cart" style={{textAlign:'center', padding:'60px 20px'}}>
                    <img src="https://cdn-icons-png.flaticon.com/512/11329/11329060.png" alt="Empty" style={{width:'120px', opacity:0.6, marginBottom:'20px'}}/>
                    <h3 style={{color:'#555', margin:'0 0 10px'}}>Giỏ hàng của bạn đang trống</h3>
                    <p style={{color:'#888', marginBottom:'30px'}}>Hãy chọn thêm vài món ngon nhé!</p>
                    <button onClick={() => navigate('/shop')} className="checkout-btn" style={{width:'auto', padding:'12px 40px', marginTop:0}}>Quay lại thực đơn</button>
                </div>
            ) : (
                <div className="cart-content">
                    <table className="cart-table">
                        <thead>
                            <tr>
                                <th style={{textAlign:'center', width:'60px'}}>STT</th>
                                <th>Món ăn</th>
                                <th style={{width:'150px'}}>Đơn giá</th>
                                <th style={{width:'160px'}}>Số lượng</th>
                                <th style={{width:'150px'}}>Thành tiền</th>
                                <th style={{width:'60px'}}></th>
                            </tr>
                        </thead>
                        <tbody>
                            {cartItems.map((item, index) => (
                                <tr key={item.food_id}>
                                    <td style={{textAlign:'center', color:'#999', fontWeight:'bold'}}>{index + 1}</td>
                                    
                                    <td>
                                        <div style={{display:'flex', alignItems:'center', gap:'20px'}}>
                                            {item.image_url ? (
                                                <img src={`${API_URL}${item.image_url}`} className="cart-thumb" alt="" />
                                            ) : (
                                                <div className="cart-thumb" style={{background:'#eee', display:'flex', alignItems:'center', justifyContent:'center', fontSize:'2rem'}}>🍖</div>
                                            )}
                                            <div style={{display:'flex', flexDirection:'column'}}>
                                                <span style={{fontWeight:'700', fontSize:'1.1rem', color:'#333'}}>{item.name}</span>
                                                <span style={{fontSize:'0.85rem', color:'#888'}}>Mã món: #{item.food_id}</span>
                                            </div>
                                        </div>
                                    </td>
                                    
                                    <td style={{fontWeight:'500', color:'#555'}}>{formatMoney(item.price)}</td>
                                    
                                    <td>
                                        <div className="qty-control">
                                            <button className="qty-btn" onClick={() => updateQuantity(item.food_id, item.quantity - 1)}><FaMinus size={10}/></button>
                                            <span className="qty-value">{item.quantity}</span>
                                            <button className="qty-btn" onClick={() => updateQuantity(item.food_id, item.quantity + 1)}><FaPlus size={10}/></button>
                                        </div>
                                    </td>
                                    
                                    <td style={{fontWeight:'800', color:'#ff6347', fontSize:'1.1rem'}}>{formatMoney(item.price * item.quantity)}</td>
                                    
                                    <td style={{textAlign:'center'}}>
                                        <button className="btn-remove" onClick={() => removeItem(item.food_id)} title="Xóa món này"><FaTrash size={16}/></button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>

                    <div className="cart-summary-box">
                        <h3 style={{marginTop:0, marginBottom:'20px'}}>Tổng kết đơn hàng</h3>
                        
                        <div className="coupon-section">
                            <input placeholder="Mã giảm giá (VD: SALE50)" value={couponCode} onChange={e => setCouponCode(e.target.value.toUpperCase())} />
                            <button onClick={handleApplyCoupon}>Áp dụng</button>
                        </div>
                        
                        <div className="summary-row">
                            <span>Tạm tính</span>
                            <span style={{fontWeight:'600'}}>{formatMoney(subTotal)}</span>
                        </div>
                        
                        {appliedCoupon && (
                            <div className="summary-row" style={{color:'#27ae60'}}>
                                <span>Giảm giá ({appliedCoupon.code})</span>
                                <span>- {formatMoney(subTotal * appliedCoupon.discount_percent / 100)}</span>
                            </div>
                        )}
                        
                        <div className="summary-row total">
                            <span>Tổng tiền</span>
                            <span style={{color:'#ff4757'}}>{formatMoney(totalPrice)}</span>
                        </div>

                        <button className="checkout-btn" onClick={handleCheckout}>Tiến hành thanh toán</button>
                    </div>
                </div>
            )}
        </div>
    );
}

export default Cart;