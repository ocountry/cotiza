import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
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
  Send,
  Phone,
  AlertCircle,
  StickyNote
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AddItem() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [url, setUrl] = useState('');
  const [method, setMethod] = useState('scraping');
  const [channels, setChannels] = useState(['email']);
  const [notes, setNotes] = useState('');
  const [preview, setPreview] = useState(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [creating, setCreating] = useState(false);
  const [siteNotSupported, setSiteNotSupported] = useState(false);

  // Check which channels are configured
  const configuredChannels = {
    email: !!user?.notification_email,
    whatsapp: !!user?.notification_whatsapp,
    telegram: !!user?.notification_telegram,
    sms: !!user?.notification_sms,
  };

  const handlePreview = async () => {
    if (!url.trim()) {
      toast.error('Por favor ingresa una URL');
      return;
    }

    setLoadingPreview(true);
    setPreview(null);
    setSiteNotSupported(false);
    
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
        
        // Check if price was detected - if not, mark site as not supported
        if (data.price === null || data.price === undefined) {
          setSiteNotSupported(true);
        }
      } else {
        toast.error('Error al obtener vista previa');
        setSiteNotSupported(true);
      }
    } catch (error) {
      toast.error('Error de conexión con el servidor');
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

    // Check if selected channels are configured
    const unconfiguredChannels = channels.filter(ch => !configuredChannels[ch]);
    if (unconfiguredChannels.length > 0) {
      toast.warning(`Configura ${unconfiguredChannels.join(', ')} en Ajustes para recibir notificaciones`);
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
          notes: notes.trim() || null,
        }),
      });
      
      if (response.ok) {
        toast.success('¡Item agregado exitosamente!');
        navigate('/dashboard');
      } else {
        const data = await response.json();
        toast.error(data.detail || 'Error al crear item');
      }
    } catch (error) {
      toast.error('Error al crear item');
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
    if (price === null || price === undefined) return 'No detectado';
    
    // Format based on currency
    const currencyConfig = {
      CLP: { locale: 'es-CL', maximumFractionDigits: 0 },
      USD: { locale: 'en-US', maximumFractionDigits: 2 },
      EUR: { locale: 'de-DE', maximumFractionDigits: 2 },
      MXN: { locale: 'es-MX', maximumFractionDigits: 2 },
      ARS: { locale: 'es-AR', maximumFractionDigits: 2 },
    };
    
    const config = currencyConfig[currency] || currencyConfig.USD;
    
    return new Intl.NumberFormat(config.locale, {
      style: 'currency',
      currency,
      maximumFractionDigits: config.maximumFractionDigits,
    }).format(price);
  };

  const channelsList = [
    { id: 'email', icon: Mail, label: 'Email', configured: configuredChannels.email },
    { id: 'whatsapp', icon: MessageCircle, label: 'WhatsApp', configured: configuredChannels.whatsapp },
    { id: 'telegram', icon: Send, label: 'Telegram', configured: configuredChannels.telegram },
    { id: 'sms', icon: Phone, label: 'SMS', configured: configuredChannels.sms },
  ];

  const hasAnyChannelConfigured = Object.values(configuredChannels).some(Boolean);

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
                URL del Producto
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-3">
                <Input
                  type="url"
                  placeholder="https://ejemplo.com/producto"
                  value={url}
                  onChange={(e) => {
                    setUrl(e.target.value);
                    setSiteNotSupported(false);
                    setPreview(null);
                  }}
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
                      Vista Previa
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

          {/* Notification Channels */}
          <Card className="bg-card border border-border/50 rounded-sm">
            <CardHeader>
              <CardTitle className="font-heading text-xl">Notification Channels</CardTitle>
              <CardDescription>
                Select which channels to notify when the price changes
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {!hasAnyChannelConfigured && (
                <div className="flex items-start gap-3 p-4 bg-warning/10 border border-warning/30 rounded-sm">
                  <AlertCircle className="w-5 h-5 text-warning flex-shrink-0 mt-0.5" strokeWidth={1.5} />
                  <div>
                    <p className="text-sm font-medium">No channels configured</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Go to <Link to="/settings" className="text-accent underline">Settings</Link> to configure your notification accounts (email, WhatsApp, etc.)
                    </p>
                  </div>
                </div>
              )}
              
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {channelsList.map((channel) => (
                  <Label
                    key={channel.id}
                    className={`flex flex-col items-center gap-2 p-4 border rounded-sm cursor-pointer transition-colors ${
                      channels.includes(channel.id) ? 'border-accent bg-accent/5' : 'border-border'
                    } ${!channel.configured ? 'opacity-60' : ''}`}
                  >
                    <Checkbox
                      checked={channels.includes(channel.id)}
                      onCheckedChange={() => toggleChannel(channel.id)}
                      data-testid={`channel-${channel.id}`}
                    />
                    <channel.icon className="w-5 h-5 text-muted-foreground" strokeWidth={1.5} />
                    <span className="text-sm">{channel.label}</span>
                    {!channel.configured && (
                      <span className="text-xs text-warning">Not configured</span>
                    )}
                  </Label>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Site Not Supported Message */}
          {siteNotSupported && (
            <Card className="bg-warning/5 border border-warning/30 rounded-sm animate-slide-up">
              <CardContent className="pt-6">
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 bg-warning/20 rounded-full flex items-center justify-center flex-shrink-0">
                    <AlertCircle className="w-5 h-5 text-warning" strokeWidth={1.5} />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-heading text-lg text-warning mb-2">
                      Sitio no habilitado
                    </h3>
                    <p className="text-muted-foreground text-sm leading-relaxed">
                      Por el momento no se puede obtener la información desde el sitio del producto ya que la tienda no está habilitada en el sistema. El equipo ha sido notificado y pronto lo habilitará. Te enviaremos una notificación a tu correo cuando esté disponible.
                    </p>
                    <p className="text-muted-foreground text-sm mt-3">
                      Puedes intentar con el método de <span className="text-accent font-medium">extracción con IA</span> si aún no lo has probado.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Preview */}
          {preview && (
            <Card className="bg-card border border-accent/30 rounded-sm animate-slide-up">
              <CardHeader>
                <CardTitle className="font-heading text-xl">Vista Previa</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {preview.image_url && (
                  <img 
                    src={preview.image_url} 
                    alt={preview.title || 'Producto'}
                    className="w-full h-48 object-cover rounded-sm"
                    onError={(e) => e.target.style.display = 'none'}
                  />
                )}
                <div>
                  <h3 className="font-heading text-2xl mb-2">
                    {preview.title || 'Título no detectado'}
                  </h3>
                  {preview.description && (
                    <p className="text-muted-foreground text-sm line-clamp-3">
                      {preview.description}
                    </p>
                  )}
                </div>
                <div className="flex items-center justify-between pt-4 border-t border-border/50">
                  <div>
                    <span className="text-muted-foreground text-sm block">Precio Detectado</span>
                    <span className="text-xs text-muted-foreground">Moneda: {preview.currency || 'USD'}</span>
                  </div>
                  <span className={`text-3xl font-heading ${siteNotSupported ? 'text-warning' : ''}`}>
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
              Cancelar
            </Button>
            <Button
              onClick={handleCreate}
              disabled={creating || !url.trim() || siteNotSupported}
              className="flex-1 rounded-full h-12 px-8 uppercase tracking-widest text-xs font-bold btn-hover-scale"
              data-testid="create-btn"
            >
              {creating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : siteNotSupported ? (
                'Sitio no soportado'
              ) : (
                'Comenzar a Rastrear'
              )}
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
}
