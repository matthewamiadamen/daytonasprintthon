import dragonAvatar from "@/assets/dragon-avatar.png";

const ParallaxAvatar = () => (
  <div className="relative w-44 h-44 mx-auto animate-float">
    {/* Outer glow */}
    <div className="absolute inset-0 rounded-full bg-violet/30 blur-3xl" />
    <div className="absolute inset-0 rounded-full bg-violet-light/20 blur-2xl" />
    {/* Dragon avatar */}
    <img
      src={dragonAvatar}
      alt="Parallax Dragon"
      width={512}
      height={512}
      className="relative w-full h-full object-contain drop-shadow-[0_0_30px_rgba(124,58,237,0.5)]"
    />
  </div>
);

export default ParallaxAvatar;
