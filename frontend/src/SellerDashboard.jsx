import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { 
    FaSignOutAlt, FaBoxOpen, FaClipboardList, FaTags, 
    FaPlus, FaTrash, FaUpload, FaCheck, FaTimes, FaTruck, FaEdit 
} from "react-icons/fa"; 
import api from './api';

const API_BASE_URL = "http://localhost:8000"; 
const WS_URL = "ws://localhost:8006";

function SellerDashboard() {
    // --- STATE ---
    const [stats, setStats] = useState({ revenue: 0, orders: 0, pending: 0, totalFoods: 0 });
    const [orders, setOrders] = useState([]);
    const [foods, setFoods] = useState([]);
    const [coupons, setCoupons] = useState([]);
    
    const [activeTab, setActiveTab] = useState('orders');
    const [showModal, setShowModal] = useState(null); 
    const [loading, setLoading] = useState(false);
    
    // FORM STATE
    const [newFood, setNewFood] = useState({ name: '', price: '', description: '' });
    const [foodImageFile, setFoodImageFile] = useState(null); 
    const [previewImage, setPreviewImage] = useState(null);
    const [newCoupon, setNewCoupon] = useState({ code: '', discount_percent: '', valid_from: '', valid_to: '' });

    const [editingFoodId, setEditingFoodId] = useState(null);

    const navigate = useNavigate();

    useEffect(() => {
        const branchId = localStorage.getItem('branch_id');
        const role = localStorage.getItem('role');
        if (role !== 'seller') { navigate('/'); return; }
        if (!branchId) { toast.error("Vui lòng đăng nhập lại!"); navigate('/login'); return; }
        
        fetchAllData(branchId);
        
        const ws = new WebSocket(`${WS_URL}/ws/${branchId}`);
        ws.onopen = () => console.log("🟢 WebSocket Connected");
        ws.onmessage = (event) => {
            toast.info(`🔔 ${event.data}`, { autoClose: 8000, theme: "colored" });
            fetchAllData(branchId);
        };
        return () => { if (ws.readyState === 1) ws.close(); };
    }, []);

    const fetchAllData = async (branchId) => {
        try {
            const [resFoods, resOrders, resCoupons] = await Promise.all([
                api.get('/foods', { params: { branch_id: branchId } }),
                api.get('/orders', { params: { branch_id: branchId } }),
                api.get('/coupons', { params: { branch_id: branchId } }).catch(() => ({ data: [] }))
            ]);
            setFoods(resFoods.data || []);
            setOrders((resOrders.data || []).sort((a, b) => new Date(b.created_at) - new Date(a.created_at)));
            setCoupons(resCoupons.data || []);
            
            const revenue = (resOrders.data || []).filter(o => o.status === 'COMPLETED' || o.status === 'PAID').reduce((sum, o) => sum + (o.total_price || 0), 0);
            setStats({ revenue, orders: (resOrders.data || []).length, pending: (resOrders.data || []).filter(o => o.status === 'PENDING' || o.status === 'PAID').length, totalFoods: (resFoods.data || []).length });
        } catch (err) { console.error(err); }
    };

    const updateOrderStatus = async (orderId, newStatus) => {
        try {
            await api.put(`/orders/${orderId}/status`, null, { params: { status: newStatus } });
            toast.success(`Đơn #${orderId} -> ${newStatus}`);
            fetchAllData(localStorage.getItem('branch_id'));
        } catch (err) { toast.error("Lỗi cập nhật"); }
    };

    // --- LOGIC MÓN ĂN ---
    const openAddModal = () => {
        setEditingFoodId(null);
        setNewFood({ name: '', price: '', description: '' });
        setFoodImageFile(null);
        setPreviewImage(null);
        setShowModal('food');
    };

    const openEditModal = (food) => {
        setEditingFoodId(food.id);
        setNewFood({ name: food.name, price: food.price, description: food.description || '' });
        setFoodImageFile(null);
        setPreviewImage(food.image_url ? `${API_BASE_URL}${food.image_url}` : null);
        setShowModal('food');
    };

    const handleImageChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            setFoodImageFile(file);
            setPreviewImage(URL.createObjectURL(file));
        }
    };

    const handleSaveFood = async () => {
        if (!newFood.name || !newFood.price) return toast.warning("Nhập tên và giá!");
        setLoading(true);
        try {
            const branchId = localStorage.getItem('branch_id');
            const formData = new FormData();
            formData.append('name', newFood.name);
            formData.append('price', newFood.price);
            formData.append('description', newFood.description || "");
            formData.append('branch_id', branchId); 
            if (foodImageFile) formData.append('image', foodImageFile);

            if (editingFoodId) {
                await api.put(`/foods/${editingFoodId}`, formData, { headers: { 'Content-Type': 'multipart/form-data' } });
                toast.success("Cập nhật thành công!");
            } else {
                await api.post('/foods', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
                toast.success("Thêm mới thành công!");
            }
            setShowModal(null);
            fetchAllData(branchId); 
        } catch (err) { toast.error("Lỗi lưu món"); } finally { setLoading(false); }
    };

    const handleDeleteFood = async (id) => {
        if(!window.confirm("Xóa món này?")) return;
        try { await api.delete(`/foods/${id}`); toast.success("Đã xóa"); fetchAllData(localStorage.getItem('branch_id')); } catch (e) { toast.error("Lỗi xóa"); }
    };

    // --- LOGIC COUPON (FIX LỖI 422) ---
    const handleAddCoupon = async () => {
        // 1. Kiểm tra dữ liệu đầu vào
        if (!newCoupon.code || !newCoupon.discount_percent) {
            return toast.warning("Vui lòng nhập Mã và % Giảm giá!");
        }

        const branchId = localStorage.getItem('branch_id');
        if (!branchId) {
            return toast.error("Lỗi: Không tìm thấy ID chi nhánh. Hãy đăng nhập lại.");
        }

        setLoading(true);
        try {
            // 2. Chuẩn hóa dữ liệu trước khi gửi
            const payload = {
                code: newCoupon.code.toUpperCase(),
                discount_percent: parseInt(newCoupon.discount_percent) || 0, // Đảm bảo là số nguyên
                branch_id: parseInt(branchId), // Đảm bảo là số nguyên
                
                // Xử lý ngày tháng: Nếu không chọn thì lấy ngày hiện tại
                start_date: newCoupon.valid_from ? new Date(newCoupon.valid_from).toISOString() : new Date().toISOString(),
                end_date: newCoupon.valid_to ? new Date(newCoupon.valid_to).toISOString() : new Date().toISOString(),
            };
            
            await api.post('/coupons', payload);
            
            toast.success("Tạo mã thành công!");
            setShowModal(null);
            setNewCoupon({ code: '', discount_percent: '', valid_from: '', valid_to: '' });
            fetchAllData(branchId);
        } catch (err) {
            // Hiển thị lỗi chi tiết từ backend nếu có
            console.error(err);
            toast.error("Lỗi tạo mã: " + (err.response?.data?.detail || "Kiểm tra lại dữ liệu")); 
        } finally { 
            setLoading(false); 
        }
    };

    const handleDeleteCoupon = async (id) => {
        if(!window.confirm("Xóa mã này?")) return;
        try { await api.delete(`/coupons/${id}`); toast.success("Đã xóa"); fetchAllData(localStorage.getItem('branch_id')); } catch (e) { toast.error("Lỗi xóa"); }
    };

    const handleLogout = () => { localStorage.clear(); navigate('/'); };
    const formatMoney = (val) => new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(val);
    const formatDate = (iso) => iso ? new Date(iso).toLocaleString('vi-VN') : '---';
    const renderStatusBadge = (status) => { const colors = { 'PENDING': 'orange', 'PAID': '#28a745', 'PREPARING': '#17a2b8', 'SHIPPING': '#007bff', 'COMPLETED': 'gray', 'CANCELLED': 'red' }; return <span style={{background: colors[status] || '#333', color:'white', padding:'4px 10px', borderRadius:'12px', fontSize:'0.8rem', fontWeight:'bold'}}>{status}</span>; };
    const tabStyle = (name) => ({ padding:'10px 20px', border:'none', borderRadius:'30px', cursor:'pointer', fontWeight:'bold', display:'flex', gap:'8px', alignItems:'center', transition:'0.2s', background: activeTab === name ? '#ff6347' : '#eee', color: activeTab === name ? 'white' : '#333', outline: 'none' });

    return (
        <div className="seller-container" style={{maxWidth: '1200px', margin: '0 auto', padding: '20px'}}>
            <div className="seller-header" style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'30px', borderBottom:'1px solid #eee', paddingBottom:'20px'}}>
                <div><h2 className="seller-brand" style={{margin:0, color:'#ff6347'}}>FOOD ORDER</h2><span style={{color:'#777'}}>Kênh Quản Lý</span></div>
                <button onClick={handleLogout} className="icon-btn logout"><FaSignOutAlt/></button>
            </div>
            
            <div className="stat-grid" style={{display:'grid', gridTemplateColumns:'repeat(4, 1fr)', gap:'20px', marginBottom:'30px'}}>
                <div className="stat-card" style={{borderLeft:'5px solid #28a745', padding:'20px', background:'white', boxShadow:'0 2px 5px rgba(0,0,0,0.05)'}}><h3>Doanh thu</h3><div className="value" style={{color:'#28a745', fontSize:'1.5rem', fontWeight:'bold'}}>{formatMoney(stats.revenue)}</div></div>
                <div className="stat-card" style={{borderLeft:'5px solid #17a2b8', padding:'20px', background:'white', boxShadow:'0 2px 5px rgba(0,0,0,0.05)'}}><h3>Đơn hàng</h3><div className="value" style={{fontSize:'1.5rem', fontWeight:'bold'}}>{stats.orders}</div></div>
                <div className="stat-card" style={{borderLeft:'5px solid #ffc107', padding:'20px', background:'white', boxShadow:'0 2px 5px rgba(0,0,0,0.05)'}}><h3>Chờ xử lý</h3><div className="value" style={{color:'#ffc107', fontSize:'1.5rem', fontWeight:'bold'}}>{stats.pending}</div></div>
                <div className="stat-card" style={{borderLeft:'5px solid #6c757d', padding:'20px', background:'white', boxShadow:'0 2px 5px rgba(0,0,0,0.05)'}}><h3>Tổng món</h3><div className="value" style={{color:'#6c757d', fontSize:'1.5rem', fontWeight:'bold'}}>{stats.totalFoods}</div></div>
            </div>

            <div style={{display:'flex', gap:'15px', marginBottom:'20px'}}>
                <button onClick={()=>setActiveTab('orders')} style={tabStyle('orders')}><FaClipboardList/> Đơn hàng</button>
                <button onClick={()=>setActiveTab('foods')} style={tabStyle('foods')}><FaBoxOpen/> Thực đơn</button>
                <button onClick={()=>setActiveTab('coupons')} style={tabStyle('coupons')}><FaTags/> Mã giảm giá</button>
            </div>

            {/* TAB ĐƠN HÀNG */}
            {activeTab === 'orders' && (
                <div style={{background:'white', borderRadius:'8px', overflow:'hidden', boxShadow:'0 2px 10px rgba(0,0,0,0.05)'}}>
                    <table className="data-table" style={{width:'100%', borderCollapse:'collapse'}}>
                        <thead style={{background:'#f8f9fa'}}><tr><th style={{padding:'15px'}}>Mã</th><th style={{padding:'15px'}}>Khách</th><th style={{padding:'15px'}}>Món</th><th style={{padding:'15px'}}>Tổng tiền</th><th style={{padding:'15px'}}>Trạng thái</th><th style={{padding:'15px'}}>Thao tác</th></tr></thead>
                        <tbody>
                            {orders.map(o => (
                                <tr key={o.id} style={{borderBottom:'1px solid #eee'}}>
                                    <td style={{padding:'15px'}}><strong>#{o.id}</strong></td>
                                    <td style={{padding:'15px'}}>{o.customer_name}<br/><small>{formatDate(o.created_at)}</small></td>
                                    <td style={{padding:'15px', maxWidth:'300px'}}>{o.items?.map((i, idx) => <div key={idx}><b>{i.quantity}x</b> {i.food_name}</div>)}</td>
                                    <td style={{padding:'15px'}}>
                                        <div style={{fontWeight:'bold'}}>{formatMoney(o.total_price)}</div>
                                        <div style={{fontSize:'0.75rem', marginTop:'5px'}}>{o.payment_method === 'COD' ? 'Tiền mặt (COD)' : 'Chuyển khoản'}</div>
                                    </td>
                                    <td style={{padding:'15px'}}>{renderStatusBadge(o.status)}</td>
                                    <td style={{padding:'15px'}}>
                                        <div style={{display:'flex', gap:'5px', flexDirection:'column'}}>
                                            {(o.status === 'PENDING' || o.status === 'PAID') && <><button onClick={()=>updateOrderStatus(o.id, 'PREPARING')} style={{background:'#28a745', color:'white', border:'none', padding:'5px', borderRadius:'4px', cursor:'pointer'}}><FaCheck/> Nhận</button><button onClick={()=>updateOrderStatus(o.id, 'CANCELLED')} style={{background:'#dc3545', color:'white', border:'none', padding:'5px', borderRadius:'4px', cursor:'pointer'}}><FaTimes/> Hủy</button></>}
                                            {o.status === 'PREPARING' && <button onClick={()=>updateOrderStatus(o.id, 'SHIPPING')} style={{background:'#007bff', color:'white', border:'none', padding:'5px', borderRadius:'4px', cursor:'pointer'}}><FaTruck/> Giao hàng</button>}
                                            {o.status === 'SHIPPING' && <small>Đang giao...</small>}
                                            {o.status === 'COMPLETED' && <small style={{color:'green'}}>Hoàn tất</small>}
                                            {o.status === 'CANCELLED' && <small style={{color:'red'}}>Đã hủy</small>}
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* TAB THỰC ĐƠN */}
            {activeTab === 'foods' && (
                <div>
                    <div style={{display:'flex', justifyContent:'space-between', marginBottom:'20px'}}>
                        <h3>Danh sách món ăn</h3>
                        <button onClick={openAddModal} style={{background:'#28a745', color:'white', padding:'10px 20px', borderRadius:'6px', border:'none', fontWeight:'bold', cursor:'pointer', display:'flex', alignItems:'center', gap:'8px'}}><FaPlus/> Thêm món</button>
                    </div>
                    <div style={{background:'white', borderRadius:'8px', overflow:'hidden', boxShadow:'0 2px 10px rgba(0,0,0,0.05)'}}>
                        <table className="data-table" style={{width:'100%', borderCollapse:'collapse'}}>
                            <thead style={{background:'#f8f9fa'}}><tr><th style={{padding:'15px'}}>Hình</th><th style={{padding:'15px'}}>Tên</th><th style={{padding:'15px'}}>Giá</th><th style={{padding:'15px'}}>Thao tác</th></tr></thead>
                            <tbody>
                                {foods.map(f => (
                                    <tr key={f.id} style={{borderBottom:'1px solid #eee'}}>
                                        <td style={{padding:'15px'}}><img src={f.image_url ? `${API_BASE_URL}${f.image_url}` : 'https://via.placeholder.com/50'} style={{width:'60px', height:'60px', objectFit:'cover', borderRadius:'6px'}} alt=""/></td>
                                        <td style={{padding:'15px'}}>{f.name}</td>
                                        <td style={{padding:'15px', color:'#d32f2f', fontWeight:'bold'}}>{formatMoney(f.price)}</td>
                                        <td style={{padding:'15px', textAlign:'center'}}>
                                            <button onClick={() => openEditModal(f)} style={{color:'#ffc107', background:'none', border:'none', marginRight:'10px', cursor:'pointer'}}><FaEdit/></button>
                                            <button onClick={()=>handleDeleteFood(f.id)} style={{color:'#dc3545', background:'none', border:'none', cursor:'pointer'}}><FaTrash/></button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* TAB COUPON */}
            {activeTab === 'coupons' && (
                <div>
                    <div style={{display:'flex', justifyContent:'space-between', marginBottom:'20px'}}>
                        <h3>Danh sách Mã giảm giá</h3>
                        <button onClick={()=>setShowModal('coupon')} style={{background:'#007bff', color:'white', padding:'10px 20px', borderRadius:'6px', border:'none', fontWeight:'bold', cursor:'pointer'}}><FaPlus/> Tạo mã mới</button>
                    </div>
                    <div style={{background:'white', borderRadius:'8px', overflow:'hidden', boxShadow:'0 2px 10px rgba(0,0,0,0.05)'}}>
                        <table className="data-table" style={{width:'100%', borderCollapse:'collapse'}}>
                            <thead style={{background:'#f8f9fa'}}><tr><th style={{padding:'15px'}}>Code</th><th style={{padding:'15px'}}>Giảm</th><th style={{padding:'15px'}}>Hạn dùng</th><th style={{padding:'15px'}}>Xóa</th></tr></thead>
                            <tbody>
                                {coupons.map(c=>(<tr key={c.id} style={{borderBottom:'1px solid #eee'}}><td style={{padding:'15px'}}>{c.code}</td><td style={{padding:'15px'}}>{c.discount_percent}%</td><td style={{padding:'15px'}}>{formatDate(c.end_date)}</td><td style={{padding:'15px', textAlign:'center'}}><button onClick={()=>handleDeleteCoupon(c.id)} style={{color:'red', border:'none', background:'none', cursor:'pointer'}}><FaTrash/></button></td></tr>))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* MODAL THÊM/SỬA MÓN */}
            {showModal === 'food' && (
                <div className="modal-overlay" style={{position:'fixed', top:0, left:0, right:0, bottom:0, background:'rgba(0,0,0,0.5)', display:'flex', justifyContent:'center', alignItems:'center', zIndex:1000}}>
                    <div className="modal-content" style={{background:'white', padding:'25px', borderRadius:'8px', width:'400px'}}>
                        <h3>{editingFoodId ? 'Sửa món' : 'Thêm món'}</h3>
                        <input value={newFood.name} onChange={e=>setNewFood({...newFood, name:e.target.value})} placeholder="Tên món" style={{width:'100%', padding:'10px', marginBottom:'10px', border:'1px solid #ccc'}} />
                        <input type="number" value={newFood.price} onChange={e=>setNewFood({...newFood, price:e.target.value})} placeholder="Giá bán" style={{width:'100%', padding:'10px', marginBottom:'10px', border:'1px solid #ccc'}} />
                        <input type="file" accept="image/*" onChange={handleImageChange} style={{marginBottom:'10px'}} />
                        {previewImage && <img src={previewImage} style={{height:'100px', display:'block', marginBottom:'10px'}} alt=""/>}
                        <div style={{display:'flex', justifyContent:'flex-end', gap:'10px'}}>
                            <button onClick={()=>setShowModal(null)}>Hủy</button>
                            <button onClick={handleSaveFood} style={{background:'#28a745', color:'white'}}>{loading ? 'Đang lưu...' : 'Lưu'}</button>
                        </div>
                    </div>
                </div>
            )}

            {/* MODAL TẠO MÃ - ĐÃ FIX LOGIC GỬI API */}
            {showModal === 'coupon' && (
                <div className="modal-overlay" style={{position:'fixed', top:0, left:0, right:0, bottom:0, background:'rgba(0,0,0,0.5)', display:'flex', justifyContent:'center', alignItems:'center', zIndex:1000}}>
                    <div className="modal-content" style={{background:'white', padding:'25px', borderRadius:'8px', width:'400px'}}>
                        <h3>Tạo mã giảm giá</h3>
                        <input placeholder="Mã Code" value={newCoupon.code} onChange={e=>setNewCoupon({...newCoupon, code:e.target.value.toUpperCase()})} style={{width:'100%', padding:'10px', marginBottom:'10px', border:'1px solid #ccc'}} />
                        <input placeholder="Giảm giá %" type="number" value={newCoupon.discount_percent} onChange={e=>setNewCoupon({...newCoupon, discount_percent:e.target.value})} style={{width:'100%', padding:'10px', marginBottom:'10px', border:'1px solid #ccc'}} />
                        
                        <div style={{display:'flex', gap:'10px', marginBottom:'15px'}}>
                            <input type="datetime-local" onChange={e=>setNewCoupon({...newCoupon, valid_from:e.target.value})} style={{width:'100%', padding:'8px'}} />
                            <input type="datetime-local" onChange={e=>setNewCoupon({...newCoupon, valid_to:e.target.value})} style={{width:'100%', padding:'8px'}} />
                        </div>

                        <div style={{display:'flex', gap:'10px', justifyContent:'flex-end'}}>
                            <button onClick={()=>setShowModal(null)}>Hủy</button>
                            <button onClick={handleAddCoupon} disabled={loading} style={{background:'#007bff', color:'white'}}>{loading ? 'Đang tạo...' : 'Tạo mã'}</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default SellerDashboard;