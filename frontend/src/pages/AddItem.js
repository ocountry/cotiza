import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Checkbox } from '@/components/ui/checkbox';
import { toast } from 'sonner';
import { 
  TrendingDown, 
  ArrowLeft,
  Globe,
  Sparkles,
  Search,
  Loader2,
  Mail,
  MessageCircle,
  Send
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AddItem() {
  const navigate = useNavigate();
  const [url, setUrl] = useState('');
  const [method, setMethod] = useState('scraping');
  const [channels, setChannels] = useState(['email']);
  const [endpoint, setEndpoint] = useState('');
  const [preview, setPreview] = useState(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [creating, setCreating] = useState(false);

  const handlePreview = async () => {
    if (!url.trim()) {
      toast.error('Please enter a URL');
      return;
    }

    setLoadingPreview(true);
    setPreview(null);
    
    try {
      const response = await fetch(`${API}/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ url, method }),
      });
      
      if (response.ok) {
        const data = await response.json();
        setPreview(data);
        if (!data.price && !data.title) {
          toast.warning('Could not extract data. Try AI extraction or verify the URL.');
        }
      } else {
        toast.error('Failed to preview URL');
      }
    } catch (error) {
      toast.error('Failed to connect to server');
    } finally {
      setLoadingPreview(false);
    }
  };

  const handleCreate = async () => {
    if (!url.trim()) {
      toast.error('Please enter a URL');
      return;
    }

    if (channels.length === 0) {
      toast.error('Select at least one notification channel');
      return;
    }

    setCreating(true);
    
    try {
      const response = await fetch(`${API}/items`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          url,
          extraction_method: method,
          notification_channels: channels,
          notification_endpoint: endpoint || null,
        }),
      });
      
      if (response.ok) {
        toast.success('Item added successfully!');
        navigate('/dashboard');
      } else {
        const data = await response.json();
        toast.error(data.detail || 'Failed to create item');
      }
    } catch (error) {
      toast.error('Failed to create item');
    } finally {
      setCreating(false);
    }
  };

  const toggleChannel = (channel) => {
    setChannels((prev) =>
      prev.includes(channel)
        ? prev.filter((c) => c !== channel)
        : [...prev, channel]
    );
  };

  const formatPrice = (price, currency = 'USD') => {
    if (price === null || price === undefined) return 'Not detected';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(price);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Noise overlay */}
      <div className="fixed inset-0 noise pointer-events-none" />
      
      {/* Navigation */}
      <nav className="sticky top-0 z-50 glass border-b border-border/50">
        <div className="max-w-3xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/dashboard" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-accent rounded-full flex items-center justify-center">
              <TrendingDown className="w-4 h-4 text-accent-foreground" strokeWidth={1.5} />
            </div>
            <span className="font-heading text-xl tracking-tight">Vigil</span>
          </Link>
          
          <Button 
            variant="ghost" 
            onClick={() => navigate('/dashboard')}
            className="rounded-full"
            data-testid="back-btn"
          >
            <ArrowLeft className="w-4 h-4 mr-2" strokeWidth={1.5} />
            Back
          </Button>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-3xl mx-auto px-6 py-12">
        <div className="mb-8">
          <h1 className="text-3xl md:text-4xl font-heading tracking-tight mb-2">
            Track New Item
          </h1>
          <p className="text-muted-foreground">
            Enter a product URL to start monitoring its price
          </p>
        </div>

        <div className="space-y-8">
          {/* URL Input */}
          <Card className="bg-card border border-border/50 rounded-sm">
            <CardHeader>
              <CardTitle className="font-heading text-xl flex items-center gap-2">
                <Globe className="w-5 h-5 text-accent" strokeWidth={1.5} />
                Product URL
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-3">
                <Input
                  type="url"
                  placeholder="https://example.com/product"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  className="flex-1 h-12 px-4 rounded-sm bg-background border-border"
                  data-testid="url-input"
                />
                <Button
                  variant="outline"
                  onClick={handlePreview}
                  disabled={loadingPreview || !url.trim()}
                  className="rounded-full h-12 px-6 uppercase tracking-widest text-xs font-bold"
                  data-testid="preview-btn"
                >
                  {loadingPreview ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <Search className="w-4 h-4 mr-2" strokeWidth={1.5} />
                      Preview
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Extraction Method */}
          <Card className="bg-card border border-border/50 rounded-sm">
            <CardHeader>
              <CardTitle className="font-heading text-xl flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-accent" strokeWidth={1.5} />
                Extraction Method
              </CardTitle>
            </CardHeader>
            <CardContent>
              <RadioGroup value={method} onValueChange={setMethod} className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Label
                  htmlFor="scraping"
                  className={`flex items-start gap-4 p-4 border rounded-sm cursor-pointer transition-colors ${
                    method === 'scraping' ? 'border-accent bg-accent/5' : 'border-border'
                  }`}
                >
                  <RadioGroupItem value="scraping" id="scraping" data-testid="method-scraping" />
                  <div className="flex-1">
                    <p className="font-medium mb-1">Basic Scraping</p>
                    <p className="text-sm text-muted-foreground">
                      Fast extraction using HTML parsing. Works well for standard e-commerce sites.
                    </p>
                  </div>
                </Label>
                
                <Label
                  htmlFor="ai"
                  className={`flex items-start gap-4 p-4 border rounded-sm cursor-pointer transition-colors ${
                    method === 'ai' ? 'border-accent bg-accent/5' : 'border-border'
                  }`}
                >
                  <RadioGroupItem value="ai" id="ai" data-testid="method-ai" />
                  <div className="flex-1">
                    <p className="font-medium mb-1">AI-Powered</p>
                    <p className="text-sm text-muted-foreground">
                      Uses GPT to analyze page content. Better for complex or dynamic pages.
                    </p>
                  </div>
                </Label>
              </RadioGroup>
            </CardContent>
          </Card>

          {/* Notification Settings */}
          <Card className="bg-card border border-border/50 rounded-sm">
            <CardHeader>
              <CardTitle className="font-heading text-xl">Notification Channels</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Label
                  className={`flex items-center gap-3 p-4 border rounded-sm cursor-pointer transition-colors ${
                    channels.includes('email') ? 'border-accent bg-accent/5' : 'border-border'
                  }`}
                >
                  <Checkbox
                    checked={channels.includes('email')}
                    onCheckedChange={() => toggleChannel('email')}
                    data-testid="channel-email"
                  />
                  <Mail className="w-4 h-4 text-muted-foreground" strokeWidth={1.5} />
                  <span>Email</span>
                </Label>
                
                <Label
                  className={`flex items-center gap-3 p-4 border rounded-sm cursor-pointer transition-colors ${
                    channels.includes('whatsapp') ? 'border-accent bg-accent/5' : 'border-border'
                  }`}
                >
                  <Checkbox
                    checked={channels.includes('whatsapp')}
                    onCheckedChange={() => toggleChannel('whatsapp')}
                    data-testid="channel-whatsapp"
                  />
                  <MessageCircle className="w-4 h-4 text-muted-foreground" strokeWidth={1.5} />
                  <span>WhatsApp</span>
                </Label>
                
                <Label
                  className={`flex items-center gap-3 p-4 border rounded-sm cursor-pointer transition-colors ${
                    channels.includes('telegram') ? 'border-accent bg-accent/5' : 'border-border'
                  }`}
                >
                  <Checkbox
                    checked={channels.includes('telegram')}
                    onCheckedChange={() => toggleChannel('telegram')}
                    data-testid="channel-telegram"
                  />
                  <Send className="w-4 h-4 text-muted-foreground" strokeWidth={1.5} />
                  <span>Telegram</span>
                </Label>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="endpoint" className="text-sm text-muted-foreground">
                  Webhook Endpoint (required for notifications)
                </Label>
                <Input
                  id="endpoint"
                  type="url"
                  placeholder="https://your-server.com/webhook"
                  value={endpoint}
                  onChange={(e) => setEndpoint(e.target.value)}
                  className="h-12 px-4 rounded-sm bg-background border-border"
                  data-testid="endpoint-input"
                />
                <p className="text-xs text-muted-foreground">
                  We'll send price change notifications to this endpoint with channel info.
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Preview */}
          {preview && (
            <Card className="bg-card border border-accent/30 rounded-sm animate-slide-up">
              <CardHeader>
                <CardTitle className="font-heading text-xl">Preview</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {preview.image_url && (
                  <img 
                    src={preview.image_url} 
                    alt={preview.title || 'Product'}
                    className="w-full h-48 object-cover rounded-sm"
                    onError={(e) => e.target.style.display = 'none'}
                  />
                )}
                <div>
                  <h3 className="font-heading text-2xl mb-2">
                    {preview.title || 'Title not detected'}
                  </h3>
                  {preview.description && (
                    <p className="text-muted-foreground text-sm line-clamp-3">
                      {preview.description}
                    </p>
                  )}
                </div>
                <div className="flex items-center justify-between pt-4 border-t border-border/50">
                  <span className="text-muted-foreground text-sm">Detected Price</span>
                  <span className="text-3xl font-heading">
                    {formatPrice(preview.price, preview.currency)}
                  </span>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Submit */}
          <div className="flex gap-4">
            <Button
              variant="outline"
              onClick={() => navigate('/dashboard')}
              className="rounded-full h-12 px-8 uppercase tracking-widest text-xs font-bold"
            >
              Cancel
            </Button>
            <Button
              onClick={handleCreate}
              disabled={creating || !url.trim()}
              className="flex-1 rounded-full h-12 px-8 uppercase tracking-widest text-xs font-bold btn-hover-scale"
              data-testid="create-btn"
            >
              {creating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                'Start Tracking'
              )}
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
}
