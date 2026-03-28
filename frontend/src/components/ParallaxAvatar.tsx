import parallaxOpen from "@/assets/parallax-logo-open.png";

const ParallaxAvatar = () => (
  <div className="relative w-56 h-56 mx-auto">
    {/* Subtle glow behind the logo */}
    <div className="absolute inset-0 rounded-full bg-violet/15 blur-3xl animate-pulse-glow" />
    {/* Parallax open logo */}
    <img
      src={parallaxOpen}
      alt="Parallax"
      className="relative w-full h-full object-contain drop-shadow-[0_0_40px_rgba(124,58,237,0.4)]"
    />
  </div>
);

export default ParallaxAvatar;
