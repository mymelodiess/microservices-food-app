import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { 
    FaSignOutAlt, FaBoxOpen, FaClipboardList, FaTags, 
    FaPlus, FaTrash, FaUpload, FaCheck, FaTimes, FaTruck 
} from "react-icons/fa"; 
import api from './api';

// Cấu hình URL
const API_BASE_URL = "http://localhost:8000"; 
const WS_URL = "ws://localhost:8006"; // Port của Notification Service

function SellerDashboard() {
    // --- STATE QUẢN LÝ DỮ LIỆU ---
    const [stats, setStats] = useState({ revenue: 0, orders: 0, pending: 0, totalFoods: 0 });
    const [orders, setOrders] = useState([]);
    const [foods, setFoods] = useState([]);
    const [coupons, setCoupons] = useState([]);
    
    // --- STATE GIAO DIỆN ---
    const [activeTab, setActiveTab] = useState('orders'); // orders | foods | coupons
    const [showModal, setShowModal] = useState(null); // null | 'food' | 'coupon'
    const [loading, setLoading] = useState(false);
    
    // --- STATE FORM (THÊM MÓN & COUPON) ---
    const [newFood, setNewFood] = useState({ name: '', price: '', description: '' });
    const [foodImageFile, setFoodImageFile] = useState(null); 
    const [previewImage, setPreviewImage] = useState(null);
    const [newCoupon, setNewCoupon] = useState({ code: '', discount_percent: '', valid_from: '', valid_to: '' });

    const navigate = useNavigate();

    // --- KHỞI TẠO & WEBSOCKET ---
    useEffect(() => {
        const branchId = localStorage.getItem('branch_id');
        const role = localStorage.getItem('role');

        if (role !== 'seller') { navigate('/'); return; }
        if (!branchId) { 
            toast.error("Vui lòng đăng nhập lại tài khoản Chủ quán!"); 
            navigate('/login');
            return; 
        }

        // 1. Tải dữ liệu lần đầu
        fetchAllData(branchId);

        // 2. Kết nối WebSocket để nhận thông báo đơn hàng
        const ws = new WebSocket(`${WS_URL}/ws/${branchId}`);

        ws.onopen = () => {
            console.log("🟢 Seller Dashboard: WebSocket Connected");
        };

        ws.onmessage = (event) => {
            const message = event.data;
            // Hiển thị thông báo Toast
            toast.info(`🔔 ${message}`, {
                position: "top-right",
                autoClose: 8000,
                hideProgressBar: false,
                closeOnClick: true,
                pauseOnHover: true,
                draggable: true,
                theme: "colored"
            });
            // Tự động tải lại dữ liệu khi có thông báo mới
            fetchAllData(branchId);
        };

        ws.onerror = (error) => {
            console.error("WebSocket error:", error);
        };

        // Cleanup khi rời trang
        return () => {
            if (ws.readyState === 1) ws.close();
        };

    }, []);

    // --- HÀM TẢI DỮ LIỆU TỔNG HỢP ---
    const fetchAllData = async (branchId) => {
        try {
            // Gọi song song 3 API để tiết kiệm thời gian
            const [resFoods, resOrders, resCoupons] = await Promise.all([
                api.get('/foods', { params: { branch_id: branchId } }),
                api.get('/orders', { params: { branch_id: branchId } }),
                api.get('/coupons', { params: { branch_id: branchId } }).catch(() => ({ data: [] })) // Coupon có thể lỗi nếu chưa có, catch riêng
            ]);

            // Cập nhật State Foods
            setFoods(resFoods.data || []);

            // Cập nhật State Orders (Sắp xếp mới nhất trước)
            const ordersData = resOrders.data || [];
            setOrders(ordersData.sort((a, b) => new Date(b.created_at) - new Date(a.created_at)));

            // Cập nhật State Coupons
            setCoupons(resCoupons.data || []);

            // Tính toán Thống kê (Revenue chỉ tính đơn đã hoàn tất hoặc đã thanh toán)
            const revenue = ordersData
                .filter(o => o.status === 'COMPLETED' || o.status === 'PAID')
                .reduce((sum, o) => sum + (o.total_price || 0), 0);

            setStats({
                revenue: revenue,
                orders: ordersData.length,
                pending: ordersData.filter(o => o.status === 'PENDING' || o.status === 'PAID').length,
                totalFoods: resFoods.data ? resFoods.data.length : 0
            });

        } catch (err) {
            console.error("Lỗi tải dữ liệu Dashboard:", err);
            // toast.error("Có lỗi khi tải dữ liệu.");
        }
    };

    // --- XỬ LÝ ĐƠN HÀNG (Order Logic) ---
    const updateOrderStatus = async (orderId, newStatus) => {
        try {
            await api.put(`/orders/${orderId}/status`, null, { params: { status: newStatus } });
            toast.success(`Đã cập nhật đơn #${orderId} sang trạng thái: ${newStatus}`);
            // Reload lại dữ liệu sau khi update
            fetchAllData(localStorage.getItem('branch_id'));
        } catch (err) {
            console.error(err);
            toast.error("Lỗi cập nhật trạng thái đơn hàng");
        }
    };

    // --- XỬ LÝ MÓN ĂN (Food Logic) ---
    const handleImageChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            setFoodImageFile(file);
            setPreviewImage(URL.createObjectURL(file));
        }
    };

    const handleAddFood = async () => {
        if (!newFood.name || !newFood.price) return toast.warning("Vui lòng nhập tên và giá món!");
        setLoading(true);
        try {
            const branchId = localStorage.getItem('branch_id');
            const formData = new FormData();
            
            formData.append('name', newFood.name);
            formData.append('price', newFood.price);
            formData.append('description', newFood.description || "");
            formData.append('branch_id', branchId); 
            
            if (foodImageFile) {
                formData.append('image', foodImageFile); 
            }

            await api.post('/foods', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });

            toast.success("Thêm món thành công!");
            
            // Reset form
            setShowModal(null);
            setNewFood({ name: '', price: '', description: '' });
            setFoodImageFile(null);
            setPreviewImage(null);
            
            // Reload data
            fetchAllData(branchId); 
        } catch (err) {
            toast.error("Lỗi thêm món: " + (err.response?.data?.detail || err.message));
        } finally { 
            setLoading(false); 
        }
    };

    const handleDeleteFood = async (id) => {
        if(!window.confirm("Bạn chắc chắn muốn xóa món này?")) return;
        try {
            await api.delete(`/foods/${id}`);
            toast.success("Đã xóa món ăn");
            fetchAllData(localStorage.getItem('branch_id'));
        } catch (e) { 
            toast.error("Lỗi xóa món"); 
        }
    };

    // --- XỬ LÝ MÃ GIẢM GIÁ (Coupon Logic) ---
    const handleAddCoupon = async () => {
        if (!newCoupon.code || !newCoupon.discount_percent) return toast.warning("Vui lòng nhập Mã và % Giảm!");
        setLoading(true);
        try {
            const branchId = localStorage.getItem('branch_id');
            const payload = {
                code: newCoupon.code.toUpperCase(),
                discount_percent: parseInt(newCoupon.discount_percent),
                branch_id: parseInt(branchId),
                start_date: newCoupon.valid_from ? new Date(newCoupon.valid_from).toISOString() : new Date().toISOString(),
                end_date: newCoupon.valid_to ? new Date(newCoupon.valid_to).toISOString() : new Date().toISOString(),
            };
            
            await api.post('/coupons', payload);
            
            toast.success("Tạo mã giảm giá thành công!");
            setShowModal(null);
            // Reset form coupon thì tùy ý, ở đây mình giữ lại hoặc clear cũng được
            setNewCoupon({ code: '', discount_percent: '', valid_from: '', valid_to: '' });
            
            fetchAllData(branchId);
        } catch (err) {
            toast.error("Lỗi tạo mã: " + (err.response?.data?.detail || err.message));
        } finally { 
            setLoading(false); 
        }
    };

    const handleDeleteCoupon = async (id) => {
        if(!window.confirm("Xóa mã giảm giá này?")) return;
        try {
            await api.delete(`/coupons/${id}`);
            toast.success("Đã xóa mã giảm giá");
            fetchAllData(localStorage.getItem('branch_id'));
        } catch (e) { 
            toast.error("Lỗi xóa mã"); 
        }
    };

    // --- HELPER FUNCTIONS ---
    const handleLogout = () => { localStorage.clear(); navigate('/'); };
    const formatMoney = (val) => new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(val);
    const formatDate = (iso) => iso ? new Date(iso).toLocaleString('vi-VN') : '---';

    const renderStatusBadge = (status) => {
        const colors = { 
            'PENDING': 'orange', 
            'PAID': '#28a745', 
            'PREPARING': '#17a2b8', 
            'SHIPPING': '#007bff', 
            'COMPLETED': 'gray', 
            'CANCELLED': 'red' 
        };
        const labels = {
            'PENDING': 'Chờ thanh toán',
            'PAID': 'Đã thanh toán',
            'PREPARING': 'Đang chuẩn bị',
            'SHIPPING': 'Đang giao',
            'COMPLETED': 'Hoàn tất',
            'CANCELLED': 'Đã hủy'
        };
        return (
            <span style={{
                background: colors[status] || '#333', 
                color:'white', 
                padding:'4px 10px', 
                borderRadius:'12px', 
                fontSize:'0.8rem', 
                fontWeight:'bold',
                whiteSpace: 'nowrap'
            }}>
                {labels[status] || status}
            </span>
        );
    };

    const tabStyle = (name) => ({
        padding:'10px 25px', 
        border:'none', 
        borderRadius:'30px', 
        cursor:'pointer', 
        fontWeight:'bold', 
        display:'flex', 
        gap:'8px', 
        alignItems:'center', 
        transition:'0.2s',
        background: activeTab === name ? '#ff6347' : '#eee', 
        color: activeTab === name ? 'white' : '#333',
        outline: 'none'
    });

    // --- RENDER GIAO DIỆN ---
    return (
        <div className="seller-container" style={{maxWidth: '1200px', margin: '0 auto', padding: '20px'}}>
            {/* 1. Header */}
            <div className="seller-header" style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'30px', borderBottom:'1px solid #eee', paddingBottom:'20px'}}>
                <div>
                    <h2 className="seller-brand" style={{margin:0, color:'#ff6347', textTransform:'uppercase'}}>FOOD ORDER</h2>
                    <span style={{color:'#777'}}>Kênh Quản Lý Đối Tác</span>
                </div>
                <div style={{display:'flex', alignItems:'center', gap:'15px'}}>
                    <div style={{textAlign:'right'}}>
                        <div style={{fontWeight:'bold'}}>Chủ quán</div>
                        <div style={{fontSize:'0.85rem', color:'#666'}}>Branch ID: {localStorage.getItem('branch_id')}</div>
                    </div>
                    <button onClick={handleLogout} className="icon-btn logout" title="Đăng xuất" style={{background:'#dc3545', color:'white', border:'none', width:'40px', height:'40px', borderRadius:'50%', cursor:'pointer', display:'flex', alignItems:'center', justifyContent:'center'}}>
                        <FaSignOutAlt/>
                    </button>
                </div>
            </div>

            {/* 2. Thống kê */}
            <div className="stat-grid" style={{display:'grid', gridTemplateColumns:'repeat(4, 1fr)', gap:'20px', marginBottom:'30px'}}>
                <div className="stat-card" style={{background:'white', padding:'20px', borderRadius:'8px', boxShadow:'0 2px 8px rgba(0,0,0,0.05)', borderLeft:'5px solid #28a745'}}>
                    <h3 style={{margin:'0 0 10px', color:'#666', fontSize:'1rem'}}>Doanh thu</h3>
                    <div className="value" style={{color:'#28a745', fontSize:'1.5rem', fontWeight:'bold'}}>{formatMoney(stats.revenue)}</div>
                </div>
                <div className="stat-card" style={{background:'white', padding:'20px', borderRadius:'8px', boxShadow:'0 2px 8px rgba(0,0,0,0.05)', borderLeft:'5px solid #17a2b8'}}>
                    <h3 style={{margin:'0 0 10px', color:'#666', fontSize:'1rem'}}>Đơn hàng</h3>
                    <div className="value" style={{color:'#333', fontSize:'1.5rem', fontWeight:'bold'}}>{stats.orders}</div>
                </div>
                <div className="stat-card" style={{background:'white', padding:'20px', borderRadius:'8px', boxShadow:'0 2px 8px rgba(0,0,0,0.05)', borderLeft:'5px solid #ffc107'}}>
                    <h3 style={{margin:'0 0 10px', color:'#666', fontSize:'1rem'}}>Chờ xử lý</h3>
                    <div className="value" style={{color:'#ffc107', fontSize:'1.5rem', fontWeight:'bold'}}>{stats.pending}</div>
                </div>
                <div className="stat-card" style={{background:'white', padding:'20px', borderRadius:'8px', boxShadow:'0 2px 8px rgba(0,0,0,0.05)', borderLeft:'5px solid #6c757d'}}>
                    <h3 style={{margin:'0 0 10px', color:'#666', fontSize:'1rem'}}>Tổng món</h3>
                    <div className="value" style={{color:'#6c757d', fontSize:'1.5rem', fontWeight:'bold'}}>{stats.totalFoods}</div>
                </div>
            </div>

            {/* 3. Menu Tabs */}
            <div style={{display:'flex', gap:'15px', marginBottom:'30px', borderBottom:'1px solid #ddd', paddingBottom:'15px'}}>
                <button onClick={()=>setActiveTab('orders')} style={tabStyle('orders')}><FaClipboardList/> Quản lý Đơn hàng</button>
                <button onClick={()=>setActiveTab('foods')} style={tabStyle('foods')}><FaBoxOpen/> Quản lý Thực đơn</button>
                <button onClick={()=>setActiveTab('coupons')} style={tabStyle('coupons')}><FaTags/> Mã giảm giá</button>
            </div>

            {/* 4. CONTENT: TAB ĐƠN HÀNG */}
            {activeTab === 'orders' && (
                <div style={{background:'white', borderRadius:'8px', overflow:'hidden', boxShadow:'0 2px 10px rgba(0,0,0,0.05)'}}>
                    <table className="data-table" style={{width:'100%', borderCollapse:'collapse'}}>
                        <thead style={{background:'#f8f9fa', borderBottom:'2px solid #eee'}}>
                            <tr>
                                <th style={{padding:'15px', textAlign:'left'}}>Mã</th>
                                <th style={{padding:'15px', textAlign:'left'}}>Khách hàng</th>
                                <th style={{padding:'15px', textAlign:'left'}}>Chi tiết món ăn</th>
                                <th style={{padding:'15px', textAlign:'left'}}>Tổng tiền</th>
                                <th style={{padding:'15px', textAlign:'left'}}>Trạng thái</th>
                                <th style={{padding:'15px', textAlign:'center'}}>Thao tác</th>
                            </tr>
                        </thead>
                        <tbody>
                            {orders.length === 0 ? (
                                <tr><td colSpan="6" style={{textAlign:'center', padding:'30px', color:'#999'}}>Chưa có đơn hàng nào</td></tr>
                            ) : (
                                orders.map(o => (
                                    <tr key={o.id} style={{borderBottom:'1px solid #eee'}}>
                                        <td style={{padding:'15px'}}><strong>#{o.id}</strong></td>
                                        <td style={{padding:'15px'}}>
                                            <div style={{fontWeight:'bold'}}>{o.customer_name || o.user_name}</div>
                                            <div style={{fontSize:'0.8rem', color:'#777'}}>{o.customer_phone}</div>
                                            <div style={{fontSize:'0.8rem', color:'#999'}}>{formatDate(o.created_at)}</div>
                                        </td>
                                        <td style={{padding:'15px', maxWidth:'300px'}}>
                                            {/* Hiển thị danh sách món ăn */}
                                            {o.items && o.items.length > 0 ? (
                                                <ul style={{paddingLeft:'15px', margin:0, fontSize:'0.9rem'}}>
                                                    {o.items.map((i, idx) => (
                                                        <li key={idx} style={{marginBottom:'4px'}}>
                                                            <b>{i.quantity}x</b> {i.food_name}
                                                        </li>
                                                    ))}
                                                </ul>
                                            ) : (
                                                <span style={{color:'#999', fontStyle:'italic'}}>Đang tải chi tiết...</span>
                                            )}
                                            {o.note && <div style={{marginTop:'5px', fontSize:'0.85rem', color:'#d63384', fontStyle:'italic'}}>Note: {o.note}</div>}
                                        </td>
                                        <td style={{padding:'15px', fontWeight:'bold', color:'#333'}}>{formatMoney(o.total_price)}</td>
                                        <td style={{padding:'15px'}}>{renderStatusBadge(o.status)}</td>
                                        <td style={{padding:'15px', textAlign:'center'}}>
                                            <div style={{display:'flex', gap:'8px', flexDirection:'column', alignItems:'center'}}>
                                                {/* Nút Nhận Đơn / Từ Chối (Chỉ hiện khi PENDING hoặc PAID) */}
                                                {(o.status === 'PENDING' || o.status === 'PAID') && (
                                                    <div style={{display:'flex', gap:'5px'}}>
                                                        <button onClick={()=>updateOrderStatus(o.id, 'PREPARING')} title="Nhận đơn" style={{background:'#28a745', color:'white', border:'none', padding:'6px 12px', borderRadius:'4px', cursor:'pointer', display:'flex', alignItems:'center', gap:'5px', fontSize:'0.85rem'}}>
                                                            <FaCheck/> Nhận
                                                        </button>
                                                        <button onClick={()=>updateOrderStatus(o.id, 'CANCELLED')} title="Từ chối" style={{background:'#dc3545', color:'white', border:'none', padding:'6px 12px', borderRadius:'4px', cursor:'pointer', display:'flex', alignItems:'center', gap:'5px', fontSize:'0.85rem'}}>
                                                            <FaTimes/> Hủy
                                                        </button>
                                                    </div>
                                                )}

                                                {/* Nút Giao Hàng (Hiện khi Đang chuẩn bị) */}
                                                {o.status === 'PREPARING' && (
                                                    <button onClick={()=>updateOrderStatus(o.id, 'SHIPPING')} style={{background:'#007bff', color:'white', border:'none', padding:'8px 15px', borderRadius:'4px', cursor:'pointer', display:'flex', alignItems:'center', gap:'5px', width:'100%', justifyContent:'center'}}>
                                                        <FaTruck/> Giao hàng
                                                    </button>
                                                )}

                                                {/* Trạng thái tĩnh */}
                                                {o.status === 'SHIPPING' && <span style={{color:'#007bff', fontSize:'0.85rem'}}>Đang giao...</span>}
                                                {o.status === 'COMPLETED' && <span style={{color:'green', fontSize:'0.85rem'}}>Hoàn tất</span>}
                                                {o.status === 'CANCELLED' && <span style={{color:'red', fontSize:'0.85rem'}}>Đã hủy</span>}
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            )}

            {/* 5. CONTENT: TAB THỰC ĐƠN */}
            {activeTab === 'foods' && (
                <div>
                    <div style={{display:'flex', justifyContent:'space-between', marginBottom:'20px'}}>
                        <h3>Danh sách món ăn</h3>
                        <button onClick={()=>setShowModal('food')} style={{background:'#28a745', color:'white', padding:'10px 20px', borderRadius:'6px', border:'none', fontWeight:'bold', cursor:'pointer', display:'flex', alignItems:'center', gap:'8px'}}>
                            <FaPlus/> Thêm món
                        </button>
                    </div>
                    
                    <div style={{background:'white', borderRadius:'8px', overflow:'hidden', boxShadow:'0 2px 10px rgba(0,0,0,0.05)'}}>
                        <table className="data-table" style={{width:'100%', borderCollapse:'collapse'}}>
                            <thead style={{background:'#f8f9fa', borderBottom:'2px solid #eee'}}>
                                <tr>
                                    <th style={{padding:'15px', textAlign:'left'}}>Hình ảnh</th>
                                    <th style={{padding:'15px', textAlign:'left'}}>Tên món</th>
                                    <th style={{padding:'15px', textAlign:'left'}}>Giá bán</th>
                                    <th style={{padding:'15px', textAlign:'center'}}>Thao tác</th>
                                </tr>
                            </thead>
                            <tbody>
                                {foods.length === 0 ? <tr><td colSpan="4" style={{textAlign:'center', padding:'30px', color:'#999'}}>Chưa có món ăn nào</td></tr> : (
                                    foods.map(f => (
                                        <tr key={f.id} style={{borderBottom:'1px solid #eee'}}>
                                            <td style={{padding:'15px'}}>
                                                <img 
                                                    src={f.image_url ? `${API_BASE_URL}${f.image_url}` : 'https://via.placeholder.com/50'} 
                                                    style={{width:'60px', height:'60px', objectFit:'cover', borderRadius:'6px', border:'1px solid #eee'}} 
                                                    alt={f.name}
                                                />
                                            </td>
                                            <td style={{padding:'15px', fontWeight:'500'}}>{f.name}</td>
                                            <td style={{padding:'15px', fontWeight:'bold', color:'#d32f2f'}}>{formatMoney(f.price)}</td>
                                            <td style={{padding:'15px', textAlign:'center'}}>
                                                <button onClick={()=>handleDeleteFood(f.id)} style={{color:'#dc3545', background:'none', border:'1px solid #dc3545', padding:'6px 12px', borderRadius:'4px', cursor:'pointer'}}>
                                                    <FaTrash/> Xóa
                                                </button>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* 6. CONTENT: TAB MÃ GIẢM GIÁ */}
            {activeTab === 'coupons' && (
                <div>
                    <div style={{display:'flex', justifyContent:'space-between', marginBottom:'20px'}}>
                        <h3>Danh sách Mã giảm giá</h3>
                        <button onClick={()=>setShowModal('coupon')} style={{background:'#007bff', color:'white', padding:'10px 20px', borderRadius:'6px', border:'none', fontWeight:'bold', cursor:'pointer', display:'flex', alignItems:'center', gap:'8px'}}>
                            <FaPlus/> Tạo mã mới
                        </button>
                    </div>
                    
                    <div style={{background:'white', borderRadius:'8px', overflow:'hidden', boxShadow:'0 2px 10px rgba(0,0,0,0.05)'}}>
                        <table className="data-table" style={{width:'100%', borderCollapse:'collapse'}}>
                            <thead style={{background:'#f8f9fa', borderBottom:'2px solid #eee'}}>
                                <tr>
                                    <th style={{padding:'15px', textAlign:'left'}}>Mã Code</th>
                                    <th style={{padding:'15px', textAlign:'left'}}>Giảm giá</th>
                                    <th style={{padding:'15px', textAlign:'left'}}>Hạn sử dụng</th>
                                    <th style={{padding:'15px', textAlign:'center'}}>Thao tác</th>
                                </tr>
                            </thead>
                            <tbody>
                                {coupons.length === 0 ? <tr><td colSpan="4" style={{textAlign:'center', padding:'30px', color:'#999'}}>Chưa có mã giảm giá nào</td></tr> : (
                                    coupons.map(c => (
                                        <tr key={c.id} style={{borderBottom:'1px solid #eee'}}>
                                            <td style={{padding:'15px'}}>
                                                <span style={{background:'#e3f2fd', padding:'5px 12px', borderRadius:'4px', color:'#007bff', fontWeight:'bold', letterSpacing:'1px'}}>
                                                    {c.code}
                                                </span>
                                            </td>
                                            <td style={{padding:'15px', fontWeight:'bold'}}>{c.discount_percent}%</td>
                                            <td style={{padding:'15px', color:'#666'}}>{formatDate(c.end_date || c.valid_to)}</td>
                                            <td style={{padding:'15px', textAlign:'center'}}>
                                                <button onClick={()=>handleDeleteCoupon(c.id)} style={{color:'#dc3545', background:'none', border:'1px solid #dc3545', padding:'6px 12px', borderRadius:'4px', cursor:'pointer'}}>
                                                    <FaTrash/> Xóa
                                                </button>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* 7. MODAL THÊM MÓN */}
            {showModal === 'food' && (
                <div className="modal-overlay" style={{position:'fixed', top:0, left:0, right:0, bottom:0, background:'rgba(0,0,0,0.5)', display:'flex', justifyContent:'center', alignItems:'center', zIndex:1000}}>
                    <div className="modal-content" style={{background:'white', padding:'25px', borderRadius:'8px', width:'400px', boxShadow:'0 5px 15px rgba(0,0,0,0.2)'}}>
                        <div className="modal-header" style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'20px'}}>
                            <h3 style={{margin:0}}>Thêm món mới</h3>
                            <button onClick={()=>setShowModal(null)} style={{background:'none', border:'none', fontSize:'1.5rem', cursor:'pointer'}}>×</button>
                        </div>
                        
                        <div className="form-group" style={{marginBottom:'15px'}}>
                            <label style={{display:'block', marginBottom:'5px', fontWeight:'500'}}>Tên món:</label>
                            <input 
                                value={newFood.name} 
                                onChange={e=>setNewFood({...newFood, name:e.target.value})} 
                                style={{width:'100%', padding:'10px', borderRadius:'4px', border:'1px solid #ccc', boxSizing:'border-box'}}
                            />
                        </div>
                        
                        <div className="form-group" style={{marginBottom:'15px'}}>
                            <label style={{display:'block', marginBottom:'5px', fontWeight:'500'}}>Giá bán (VNĐ):</label>
                            <input 
                                type="number" 
                                value={newFood.price} 
                                onChange={e=>setNewFood({...newFood, price:e.target.value})} 
                                style={{width:'100%', padding:'10px', borderRadius:'4px', border:'1px solid #ccc', boxSizing:'border-box'}}
                            />
                        </div>

                        <div className="form-group" style={{marginBottom:'20px'}}>
                            <label style={{display:'block', marginBottom:'5px', fontWeight:'500'}}>Hình ảnh:</label>
                            <div style={{border:'2px dashed #ccc', padding:'20px', textAlign:'center', cursor:'pointer', position:'relative', borderRadius:'4px', background:'#f9f9f9'}}>
                                <input 
                                    type="file" 
                                    accept="image/*" 
                                    onChange={handleImageChange} 
                                    style={{position:'absolute', top:0, left:0, width:'100%', height:'100%', opacity:0, cursor:'pointer'}} 
                                />
                                {previewImage ? (
                                    <img src={previewImage} style={{maxHeight:'150px', maxWidth:'100%'}} alt="Preview"/>
                                ) : (
                                    <div style={{color:'#777'}}>
                                        <FaUpload size={24} style={{marginBottom:'10px'}}/><br/>
                                        Nhấp để chọn ảnh
                                    </div>
                                )}
                            </div>
                        </div>

                        <div className="modal-actions" style={{display:'flex', gap:'10px', justifyContent:'flex-end'}}>
                            <button onClick={()=>setShowModal(null)} style={{padding:'10px 20px', borderRadius:'4px', border:'1px solid #ccc', background:'white', cursor:'pointer'}}>Hủy</button>
                            <button onClick={handleAddFood} disabled={loading} style={{padding:'10px 20px', borderRadius:'4px', border:'none', background:'#28a745', color:'white', fontWeight:'bold', cursor:'pointer', opacity: loading ? 0.7 : 1}}>
                                {loading ? 'Đang lưu...' : 'Lưu món'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* 8. MODAL TẠO MÃ */}
            {showModal === 'coupon' && (
                <div className="modal-overlay" style={{position:'fixed', top:0, left:0, right:0, bottom:0, background:'rgba(0,0,0,0.5)', display:'flex', justifyContent:'center', alignItems:'center', zIndex:1000}}>
                    <div className="modal-content" style={{background:'white', padding:'25px', borderRadius:'8px', width:'400px', boxShadow:'0 5px 15px rgba(0,0,0,0.2)'}}>
                        <div className="modal-header" style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'20px'}}>
                            <h3 style={{margin:0}}>Tạo mã giảm giá</h3>
                            <button onClick={()=>setShowModal(null)} style={{background:'none', border:'none', fontSize:'1.5rem', cursor:'pointer'}}>×</button>
                        </div>
                        
                        <div className="form-group" style={{marginBottom:'15px'}}>
                            <label style={{display:'block', marginBottom:'5px', fontWeight:'500'}}>Mã Code:</label>
                            <input 
                                value={newCoupon.code} 
                                onChange={e=>setNewCoupon({...newCoupon, code:e.target.value.toUpperCase()})}
                                placeholder="VD: SALE50"
                                style={{width:'100%', padding:'10px', borderRadius:'4px', border:'1px solid #ccc', boxSizing:'border-box'}}
                            />
                        </div>
                        
                        <div className="form-group" style={{marginBottom:'15px'}}>
                            <label style={{display:'block', marginBottom:'5px', fontWeight:'500'}}>Giảm giá (%):</label>
                            <input 
                                type="number" 
                                value={newCoupon.discount_percent} 
                                onChange={e=>setNewCoupon({...newCoupon, discount_percent:e.target.value})}
                                style={{width:'100%', padding:'10px', borderRadius:'4px', border:'1px solid #ccc', boxSizing:'border-box'}}
                            />
                        </div>

                        <div style={{display:'flex', gap:'15px', marginBottom:'20px'}}>
                            <div className="form-group" style={{flex:1}}>
                                <label style={{display:'block', marginBottom:'5px', fontWeight:'500'}}>Từ ngày:</label>
                                <input 
                                    type="datetime-local" 
                                    onChange={e=>setNewCoupon({...newCoupon, valid_from:e.target.value})}
                                    style={{width:'100%', padding:'8px', borderRadius:'4px', border:'1px solid #ccc'}}
                                />
                            </div>
                            <div className="form-group" style={{flex:1}}>
                                <label style={{display:'block', marginBottom:'5px', fontWeight:'500'}}>Đến ngày:</label>
                                <input 
                                    type="datetime-local" 
                                    onChange={e=>setNewCoupon({...newCoupon, valid_to:e.target.value})}
                                    style={{width:'100%', padding:'8px', borderRadius:'4px', border:'1px solid #ccc'}}
                                />
                            </div>
                        </div>

                        <div className="modal-actions" style={{display:'flex', gap:'10px', justifyContent:'flex-end'}}>
                            <button onClick={()=>setShowModal(null)} style={{padding:'10px 20px', borderRadius:'4px', border:'1px solid #ccc', background:'white', cursor:'pointer'}}>Hủy</button>
                            <button onClick={handleAddCoupon} disabled={loading} style={{padding:'10px 20px', borderRadius:'4px', border:'none', background:'#007bff', color:'white', fontWeight:'bold', cursor:'pointer', opacity: loading ? 0.7 : 1}}>
                                {loading ? 'Đang tạo...' : 'Tạo mã'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default SellerDashboard;