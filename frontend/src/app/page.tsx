import { HeroSection } from "@/components/landing/hero-section";
import { FeaturesSection } from "@/components/landing/features-section";
import { HowItWorksSection } from "@/components/landing/how-it-works-section";
import { Footer } from "@/components/landing/footer";

export default function LandingPage() {
  return (
    <main className="relative min-h-screen bg-background overflow-hidden">
      {/* Background Effects */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        {/* Top-left glow orb */}
        <div className="absolute -left-32 -top-32 h-96 w-96 rounded-full bg-green-500/20 blur-[128px]" />
        {/* Top-right glow orb */}
        <div className="absolute -right-32 top-1/4 h-80 w-80 rounded-full bg-emerald-500/15 blur-[100px]" />
        {/* Bottom glow orb */}
        <div className="absolute -bottom-32 left-1/3 h-96 w-96 rounded-full bg-teal-500/10 blur-[128px]" />
      </div>

      {/* Content */}
      <div className="relative z-10">
        <HeroSection />
        <FeaturesSection />
        <HowItWorksSection />
        <Footer />
      </div>
    </main>
  );
}
