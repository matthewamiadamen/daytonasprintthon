import { Button } from "@/components/ui/button";

interface Props {
  showAuth?: boolean;
}

const Navbar = ({ showAuth = true }: Props) => (
  <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 py-4 bg-background/60 backdrop-blur-xl border-b border-white/5">
    <span className="text-lg font-bold tracking-tight">⚡ Parallax</span>
    {showAuth && (
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
          Sign In
        </Button>
        <Button size="sm" className="bg-violet hover:bg-violet-dark text-white font-medium">
          Get Started
        </Button>
      </div>
    )}
  </nav>
);

export default Navbar;
