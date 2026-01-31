import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { useTheme } from '@/contexts/ThemeContext';
import { Button } from '@/components/ui/button';
import { 
  Bell, 
  TrendingDown, 
  Globe, 
  Zap, 
  Sun, 
  Moon, 
  Monitor,
  ArrowRight
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

export default function LandingPage() {
  const navigate = useNavigate();
  const { user, login, loading } = useAuth();
  const { theme, setTheme, resolvedTheme } = useTheme();

  useEffect(() => {
    if (user && !loading) {
      navigate('/dashboard');
    }
  }, [user, loading, navigate]);

  const features = [
    {
      icon: Globe,
      title: 'Track Any Website',
      description: 'Monitor prices from any e-commerce site, airline, hotel, or subscription service.',
    },
    {
      icon: Zap,
      title: 'Smart Extraction',
      description: 'Choose between fast scraping or AI-powered analysis for accurate price detection.',
    },
    {
      icon: Bell,
      title: 'Instant Alerts',
      description: 'Get notified via Email, WhatsApp, or Telegram when prices change.',
    },
    {
      icon: TrendingDown,
      title: 'Price History',
      description: 'Visualize price trends and make informed purchasing decisions.',
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Noise overlay */}
      <div className="fixed inset-0 noise pointer-events-none" />
      
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 glass border-b border-border/50">
        <div className="max-w-7xl mx-auto px-6 md:px-12 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-accent rounded-full flex items-center justify-center">
              <TrendingDown className="w-4 h-4 text-accent-foreground" strokeWidth={1.5} />
            </div>
            <span className="font-heading text-xl tracking-tight">Vigil</span>
          </div>
          
          <div className="flex items-center gap-4">
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
                <DropdownMenuItem onClick={() => setTheme('light')} data-testid="theme-light">
                  <Sun className="w-4 h-4 mr-2" strokeWidth={1.5} />
                  Light
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setTheme('dark')} data-testid="theme-dark">
                  <Moon className="w-4 h-4 mr-2" strokeWidth={1.5} />
                  Dark
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setTheme('system')} data-testid="theme-system">
                  <Monitor className="w-4 h-4 mr-2" strokeWidth={1.5} />
                  System
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            
            <Button 
              onClick={login}
              className="rounded-full px-6 h-10 uppercase tracking-widest text-xs font-bold"
              data-testid="login-btn"
            >
              Sign In
            </Button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-24 px-6 md:px-12 lg:px-24">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
            <div className="lg:col-span-7 space-y-8">
              <div className="space-y-2">
                <p className="text-muted-foreground uppercase tracking-overline text-xs font-medium opacity-0 animate-slide-up">
                  Price Intelligence Platform
                </p>
                <h1 className="text-5xl md:text-7xl lg:text-8xl font-heading tracking-tight opacity-0 animate-slide-up stagger-1">
                  Never Miss<br />
                  <span className="text-accent">a Deal</span>
                </h1>
              </div>
              
              <p className="text-lg md:text-xl text-muted-foreground max-w-xl opacity-0 animate-slide-up stagger-2">
                Track prices across any website. Get notified instantly when they drop. 
                Make smarter purchasing decisions with data.
              </p>
              
              <div className="flex flex-col sm:flex-row gap-4 opacity-0 animate-slide-up stagger-3">
                <Button 
                  onClick={login}
                  size="lg"
                  className="rounded-full px-8 h-14 uppercase tracking-widest text-xs font-bold btn-hover-scale"
                  data-testid="hero-cta-btn"
                >
                  Start Tracking Free
                  <ArrowRight className="ml-2 w-4 h-4" strokeWidth={1.5} />
                </Button>
                <Button 
                  variant="outline"
                  size="lg"
                  className="rounded-full px-8 h-14 uppercase tracking-widest text-xs font-bold"
                >
                  Learn More
                </Button>
              </div>
            </div>
            
            <div className="lg:col-span-5 opacity-0 animate-slide-up stagger-4">
              <div className="relative">
                <div className="absolute -inset-4 bg-accent/20 blur-3xl rounded-full" />
                <div className="relative bg-card border border-border/50 rounded-sm p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs uppercase tracking-overline text-muted-foreground">Price Alert</span>
                    <span className="text-xs text-success font-mono">-23%</span>
                  </div>
                  <div className="space-y-2">
                    <h3 className="font-heading text-2xl">MacBook Pro M4</h3>
                    <p className="text-muted-foreground text-sm">Apple Store</p>
                  </div>
                  <div className="flex items-end gap-3">
                    <span className="text-4xl font-heading">$1,899</span>
                    <span className="text-muted-foreground line-through text-lg mb-1">$2,499</span>
                  </div>
                  <div className="pt-4 border-t border-border/50">
                    <div className="flex gap-2">
                      <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                        <div className="h-full w-3/4 bg-accent rounded-full" />
                      </div>
                    </div>
                    <p className="text-xs text-muted-foreground mt-2">Lowest price in 90 days</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-24 px-6 md:px-12 lg:px-24 border-t border-border/50">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-muted-foreground uppercase tracking-overline text-xs font-medium mb-4">
              How it works
            </p>
            <h2 className="text-4xl md:text-5xl font-heading tracking-tight">
              Simple. Powerful. Precise.
            </h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <div 
                key={feature.title}
                className="group p-6 bg-card border border-border/50 rounded-sm card-hover opacity-0 animate-slide-up"
                style={{ animationDelay: `${0.1 * (index + 1)}s` }}
              >
                <div className="w-12 h-12 bg-muted rounded-full flex items-center justify-center mb-6 group-hover:bg-accent/10 transition-colors duration-300">
                  <feature.icon className="w-5 h-5 text-accent" strokeWidth={1.5} />
                </div>
                <h3 className="font-heading text-xl mb-3">{feature.title}</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 px-6 md:px-12 lg:px-24">
        <div className="max-w-4xl mx-auto text-center">
          <div className="relative">
            <div className="absolute inset-0 bg-accent/10 blur-3xl rounded-full" />
            <div className="relative bg-card border border-border/50 rounded-sm p-12 md:p-16">
              <h2 className="text-3xl md:text-4xl font-heading tracking-tight mb-6">
                Ready to save money?
              </h2>
              <p className="text-muted-foreground text-lg mb-8 max-w-xl mx-auto">
                Join thousands of smart shoppers who never overpay. Start tracking prices in seconds.
              </p>
              <Button 
                onClick={login}
                size="lg"
                className="rounded-full px-10 h-14 uppercase tracking-widest text-xs font-bold btn-hover-scale"
                data-testid="cta-btn"
              >
                Get Started — It's Free
                <ArrowRight className="ml-2 w-4 h-4" strokeWidth={1.5} />
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-6 md:px-12 border-t border-border/50">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-accent rounded-full flex items-center justify-center">
              <TrendingDown className="w-3 h-3 text-accent-foreground" strokeWidth={1.5} />
            </div>
            <span className="font-heading text-sm">Vigil</span>
          </div>
          <p className="text-muted-foreground text-xs">
            © {new Date().getFullYear()} Vigil. Price tracking made elegant.
          </p>
        </div>
      </footer>
    </div>
  );
}
