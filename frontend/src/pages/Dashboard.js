import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { useTheme } from '@/contexts/ThemeContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { toast } from 'sonner';
import { 
  Plus, 
  TrendingDown, 
  TrendingUp,
  ExternalLink,
  RefreshCw,
  Settings,
  LogOut,
  Sun,
  Moon,
  Monitor,
  Package,
  Bell,
  Sparkles,
  Globe
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function Dashboard() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshingId, setRefreshingId] = useState(null);

  useEffect(() => {
    fetchItems();
  }, []);

  const fetchItems = async () => {
    try {
      const response = await fetch(`${API}/items`, {
        credentials: 'include',
      });
      if (response.ok) {
        const data = await response.json();
        setItems(data);
      }
    } catch (error) {
      toast.error('Failed to load items');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async (itemId) => {
    setRefreshingId(itemId);
    try {
      const response = await fetch(`${API}/items/${itemId}/check`, {
        method: 'POST',
        credentials: 'include',
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.price_changed) {
          toast.success(`Price changed: $${data.old_price} → $${data.new_price}`);
        } else {
          toast.info('Price unchanged');
        }
        fetchItems();
      }
    } catch (error) {
      toast.error('Failed to check price');
    } finally {
      setRefreshingId(null);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  const formatPrice = (price, currency = 'USD') => {
    if (price === null || price === undefined) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(price);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Never';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Noise overlay */}
      <div className="fixed inset-0 noise pointer-events-none" />
      
      {/* Navigation */}
      <nav className="sticky top-0 z-50 glass border-b border-border/50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/dashboard" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-accent rounded-full flex items-center justify-center">
              <TrendingDown className="w-4 h-4 text-accent-foreground" strokeWidth={1.5} />
            </div>
            <span className="font-heading text-xl tracking-tight">Vigil</span>
          </Link>
          
          <div className="flex items-center gap-3">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="rounded-full" data-testid="theme-toggle">
                  {resolvedTheme === 'dark' ? (
                    <Moon className="w-4 h-4" strokeWidth={1.5} />
                  ) : (
                    <Sun className="w-4 h-4" strokeWidth={1.5} />
                  )}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => setTheme('light')}>
                  <Sun className="w-4 h-4 mr-2" strokeWidth={1.5} />
                  Light
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setTheme('dark')}>
                  <Moon className="w-4 h-4 mr-2" strokeWidth={1.5} />
                  Dark
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setTheme('system')}>
                  <Monitor className="w-4 h-4 mr-2" strokeWidth={1.5} />
                  System
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="rounded-full h-10 px-2" data-testid="user-menu">
                  <Avatar className="w-8 h-8">
                    <AvatarImage src={user?.picture} alt={user?.name} />
                    <AvatarFallback className="bg-accent text-accent-foreground text-xs">
                      {user?.name?.charAt(0) || 'U'}
                    </AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <div className="px-3 py-2">
                  <p className="font-medium text-sm">{user?.name}</p>
                  <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
                </div>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => navigate('/settings')} data-testid="settings-link">
                  <Settings className="w-4 h-4 mr-2" strokeWidth={1.5} />
                  Settings
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout} data-testid="logout-btn">
                  <LogOut className="w-4 h-4 mr-2" strokeWidth={1.5} />
                  Sign Out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
          <div>
            <h1 className="text-3xl md:text-4xl font-heading tracking-tight mb-2">
              Your Tracked Items
            </h1>
            <p className="text-muted-foreground">
              {items.length} {items.length === 1 ? 'item' : 'items'} being monitored
            </p>
          </div>
          
          <Button 
            onClick={() => navigate('/add')}
            className="rounded-full px-6 h-12 uppercase tracking-widest text-xs font-bold btn-hover-scale"
            data-testid="add-item-btn"
          >
            <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
            Track New Item
          </Button>
        </div>

        {/* Items Grid */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <Card key={i} className="bg-card border border-border/50 rounded-sm">
                <CardContent className="p-6">
                  <div className="space-y-4">
                    <div className="h-6 bg-muted rounded animate-pulse" />
                    <div className="h-4 bg-muted rounded w-2/3 animate-pulse" />
                    <div className="h-10 bg-muted rounded animate-pulse" />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : items.length === 0 ? (
          <Card className="bg-card border border-border/50 rounded-sm">
            <CardContent className="p-12 text-center">
              <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-6">
                <Package className="w-8 h-8 text-muted-foreground" strokeWidth={1.5} />
              </div>
              <h3 className="font-heading text-xl mb-3">No items yet</h3>
              <p className="text-muted-foreground mb-6 max-w-sm mx-auto">
                Start tracking prices by adding your first item. Paste any product URL to get started.
              </p>
              <Button 
                onClick={() => navigate('/add')}
                className="rounded-full px-6 h-10 uppercase tracking-widest text-xs font-bold"
                data-testid="empty-add-btn"
              >
                <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
                Add Your First Item
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {items.map((item) => (
              <Card 
                key={item.item_id}
                className="bg-card border border-border/50 rounded-sm card-hover cursor-pointer group"
                onClick={() => navigate(`/item/${item.item_id}`)}
                data-testid={`item-card-${item.item_id}`}
              >
                <CardContent className="p-6">
                  {/* Image */}
                  {item.image_url && (
                    <div className="mb-4 -mx-6 -mt-6">
                      <img 
                        src={item.image_url} 
                        alt={item.title}
                        className="w-full h-40 object-cover"
                        onError={(e) => e.target.style.display = 'none'}
                      />
                    </div>
                  )}
                  
                  {/* Header */}
                  <div className="flex items-start justify-between gap-3 mb-4">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-heading text-lg truncate mb-1 group-hover:text-accent transition-colors">
                        {item.title || 'Untitled Item'}
                      </h3>
                      <p className="text-xs text-muted-foreground truncate flex items-center gap-1">
                        <Globe className="w-3 h-3" strokeWidth={1.5} />
                        {new URL(item.url).hostname}
                      </p>
                    </div>
                    <div className="flex items-center gap-1">
                      {item.extraction_method === 'ai' ? (
                        <Badge variant="secondary" className="text-xs px-2 py-0.5">
                          <Sparkles className="w-3 h-3 mr-1" strokeWidth={1.5} />
                          AI
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-xs px-2 py-0.5">
                          Scrape
                        </Badge>
                      )}
                    </div>
                  </div>
                  
                  {/* Price */}
                  <div className="mb-4">
                    <span className="text-3xl font-heading">
                      {formatPrice(item.current_price, item.currency)}
                    </span>
                  </div>
                  
                  {/* Meta */}
                  <div className="flex items-center justify-between text-xs text-muted-foreground border-t border-border/50 pt-4">
                    <span className="flex items-center gap-1">
                      <Bell className="w-3 h-3" strokeWidth={1.5} />
                      {item.notification_channels?.length || 0} channels
                    </span>
                    <span>
                      Checked {formatDate(item.last_checked)}
                    </span>
                  </div>
                  
                  {/* Actions */}
                  <div className="flex items-center gap-2 mt-4">
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1 rounded-full h-9 text-xs uppercase tracking-wider"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRefresh(item.item_id);
                      }}
                      disabled={refreshingId === item.item_id}
                      data-testid={`refresh-btn-${item.item_id}`}
                    >
                      <RefreshCw className={`w-3 h-3 mr-1 ${refreshingId === item.item_id ? 'animate-spin' : ''}`} strokeWidth={1.5} />
                      Check Now
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="rounded-full h-9 w-9"
                      onClick={(e) => {
                        e.stopPropagation();
                        window.open(item.url, '_blank');
                      }}
                      data-testid={`external-link-${item.item_id}`}
                    >
                      <ExternalLink className="w-4 h-4" strokeWidth={1.5} />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
