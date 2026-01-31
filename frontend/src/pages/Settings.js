import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { useTheme } from '@/contexts/ThemeContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import { 
  TrendingDown, 
  ArrowLeft,
  Sun,
  Moon,
  Monitor,
  User,
  Palette,
  LogOut
} from 'lucide-react';

export default function Settings() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();

  const handleLogout = async () => {
    await logout();
    toast.success('Signed out successfully');
    navigate('/');
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
            Settings
          </h1>
          <p className="text-muted-foreground">
            Manage your account and preferences
          </p>
        </div>

        <div className="space-y-8">
          {/* Profile */}
          <Card className="bg-card border border-border/50 rounded-sm">
            <CardHeader>
              <CardTitle className="font-heading text-xl flex items-center gap-2">
                <User className="w-5 h-5 text-accent" strokeWidth={1.5} />
                Profile
              </CardTitle>
              <CardDescription>Your account information</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4">
                <Avatar className="w-16 h-16">
                  <AvatarImage src={user?.picture} alt={user?.name} />
                  <AvatarFallback className="bg-accent text-accent-foreground text-xl">
                    {user?.name?.charAt(0) || 'U'}
                  </AvatarFallback>
                </Avatar>
                <div>
                  <h3 className="font-medium text-lg">{user?.name}</h3>
                  <p className="text-muted-foreground text-sm">{user?.email}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Theme */}
          <Card className="bg-card border border-border/50 rounded-sm">
            <CardHeader>
              <CardTitle className="font-heading text-xl flex items-center gap-2">
                <Palette className="w-5 h-5 text-accent" strokeWidth={1.5} />
                Appearance
              </CardTitle>
              <CardDescription>Customize how Vigil looks</CardDescription>
            </CardHeader>
            <CardContent>
              <RadioGroup value={theme} onValueChange={setTheme} className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Label
                  htmlFor="theme-light"
                  className={`flex items-center gap-3 p-4 border rounded-sm cursor-pointer transition-colors ${
                    theme === 'light' ? 'border-accent bg-accent/5' : 'border-border'
                  }`}
                >
                  <RadioGroupItem value="light" id="theme-light" data-testid="theme-light" />
                  <Sun className="w-4 h-4" strokeWidth={1.5} />
                  <span>Light</span>
                </Label>
                
                <Label
                  htmlFor="theme-dark"
                  className={`flex items-center gap-3 p-4 border rounded-sm cursor-pointer transition-colors ${
                    theme === 'dark' ? 'border-accent bg-accent/5' : 'border-border'
                  }`}
                >
                  <RadioGroupItem value="dark" id="theme-dark" data-testid="theme-dark" />
                  <Moon className="w-4 h-4" strokeWidth={1.5} />
                  <span>Dark</span>
                </Label>
                
                <Label
                  htmlFor="theme-system"
                  className={`flex items-center gap-3 p-4 border rounded-sm cursor-pointer transition-colors ${
                    theme === 'system' ? 'border-accent bg-accent/5' : 'border-border'
                  }`}
                >
                  <RadioGroupItem value="system" id="theme-system" data-testid="theme-system" />
                  <Monitor className="w-4 h-4" strokeWidth={1.5} />
                  <span>System</span>
                </Label>
              </RadioGroup>
            </CardContent>
          </Card>

          {/* Danger Zone */}
          <Card className="bg-card border border-destructive/30 rounded-sm">
            <CardHeader>
              <CardTitle className="font-heading text-xl text-destructive">
                Danger Zone
              </CardTitle>
              <CardDescription>Irreversible actions</CardDescription>
            </CardHeader>
            <CardContent>
              <Button
                variant="outline"
                onClick={handleLogout}
                className="rounded-full h-10 px-6 uppercase tracking-widest text-xs font-bold text-destructive border-destructive/30 hover:bg-destructive/10 hover:text-destructive"
                data-testid="logout-btn"
              >
                <LogOut className="w-4 h-4 mr-2" strokeWidth={1.5} />
                Sign Out
              </Button>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
