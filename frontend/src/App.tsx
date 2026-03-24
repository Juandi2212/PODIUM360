/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState, useEffect, ReactNode } from "react";
import { motion, AnimatePresence } from "motion/react";
import { 
  Activity, 
  TrendingUp, 
  ShieldCheck, 
  Zap, 
  Menu, 
  X, 
  Target,
  Database,
  ArrowUpRight,
  CheckCircle2,
  ChevronDown,
  Gift
} from "lucide-react";
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer 
} from 'recharts';

// --- UI Components ---

const Badge = ({ children, className = "" }: { children: ReactNode, className?: string }) => (
  <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#1a1a1a] border border-[#333] text-[10px] uppercase tracking-widest font-mono text-[#888] ${className}`}>
    <div className="w-1.5 h-1.5 rounded-full bg-[#00ff66] animate-pulse" />
    {children}
  </div>
);

const SectionHeader = ({ eyebrow, title, description }: { eyebrow: string, title: string, description: string }) => (
  <div className="mb-12">
    <span className="font-mono text-[10px] uppercase tracking-[0.3em] text-[#00ff66] mb-4 block">{eyebrow}</span>
    <h2 className="text-4xl md:text-5xl font-bold tracking-tighter mb-6 text-white">{title}</h2>
    <p className="text-[#888] text-lg max-w-2xl leading-relaxed">{description}</p>
  </div>
);

const AccordionItem = ({ question, answer }: { question: string, answer: string }) => {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <div className="border-b border-[#222]">
      <button 
        onClick={() => setIsOpen(!isOpen)} 
        className="w-full py-6 flex justify-between items-center text-left hover:text-[#00ff66] transition-colors"
      >
        <span className="text-lg font-medium">{question}</span>
        <ChevronDown className={`transform transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`} size={20} />
      </button>
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <p className="pb-6 text-[#888] leading-relaxed">{answer}</p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// --- Mock Data ---
const ROI_DATA = [
  { name: 'Sem 1', roi: 12 },
  { name: 'Sem 2', roi: 28 },
  { name: 'Sem 3', roi: 22 },
  { name: 'Sem 4', roi: 45 },
  { name: 'Sem 5', roi: 58 },
  { name: 'Sem 6', roi: 71.1 },
];

const BOOKMAKERS = ['Bet365', 'Pinnacle', 'Betway', '1xBet', 'Betsson', 'Bwin', 'Coolbet', 'Stake'];

const FAQS = [
  {
    q: "¿Necesito saber de matemáticas o estadística?",
    a: "No. El modelo hace todos los cálculos complejos en la nube; tú solo ves la conclusión. Si el EV (Valor Esperado) es positivo, hay valor. Si no lo hay, Valior simplemente no emite señal."
  },
  {
    q: "¿Funciona con montos pequeños (bankrolls bajos)?",
    a: "Sí. El Valor Esperado funciona exactamente igual con $5 que con $500. El tamaño de tu bankroll no cambia la ventaja matemática (Edge) que tienes sobre el mercado."
  },
  {
    q: "¿Garantizan ganancias seguras todos los días?",
    a: "No, y huye de quien te lo prometa. El EV positivo implica una ventaja matemática a largo plazo. Cada pick individual puede ganar o perder (varianza), pero la estadística dicta que ganarás a la larga. Nuestro historial es 100% transparente al respecto."
  },
  {
    q: "¿Qué diferencia a Valior de un tipster de Telegram?",
    a: "Un tipster opina basado en intuición o 'corazonadas'. Valior calcula. Cada señal viene con el EV exacto, la probabilidad real del modelo y la cuota que la genera. Cero sesgos, 100% datos."
  }
];

const TESTIMONIALS = [
  {
    name: "Carlos M.",
    handle: "@carlos_bets",
    text: "Dejé de apostar por intuición. Valior me mostró que el 90% de mis picks no tenían EV positivo. Primer mes usando solo sus señales VIP: +14 unidades limpias.",
    verified: true
  },
  {
    name: "David Analytics",
    handle: "@david_data",
    text: "La transparencia del track record es brutal. Nadie más publica sus rojos. Llevo 3 meses y el ROI del 70% es real. Es una herramienta de inversión, no de apuestas.",
    verified: true
  },
  {
    name: "Mario R.",
    handle: "@mario_invest",
    text: "Lo mejor no son las ganancias, es la tranquilidad. Entras, ves el edge, metes el pick y cierras la app. Cero estrés, cero ver partidos sufriendo.",
    verified: true
  }
];

export default function App() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#f0f0f0] font-sans selection:bg-[#00ff66] selection:text-black">
      {/* Grain Overlay */}
      <div className="fixed inset-0 pointer-events-none z-50 opacity-[0.03] mix-blend-overlay bg-[url('https://grainy-gradients.vercel.app/noise.svg')]" />

      {/* Navigation */}
      <nav className={`fixed top-0 left-0 right-0 z-40 transition-all duration-300 border-b ${scrolled ? 'bg-[#0a0a0a]/80 backdrop-blur-md border-[#222] py-3' : 'bg-transparent border-transparent py-6'}`}>
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between">
          <a href="#" className="flex items-center gap-3 group">
            <div className="w-10 h-10 bg-[#111] border border-[#222] rounded-lg flex items-center justify-center group-hover:border-[#00ff66] transition-colors">
              <Activity size={20} className="text-[#00ff66]" />
            </div>
            <span className="text-xl font-bold tracking-tighter uppercase italic">Valior</span>
          </a>

          <div className="hidden md:flex items-center gap-8">
            {['Modelo', 'Track Record', 'Planes'].map((item) => (
              <a key={item} href={`#${item.toLowerCase().replace(' ', '-')}`} className="text-xs uppercase tracking-widest text-[#888] hover:text-[#00ff66] transition-colors">
                {item}
              </a>
            ))}
            <a href="/auth.html" className="bg-[#00ff66] text-black px-6 py-2 rounded-full text-xs font-bold uppercase tracking-widest hover:bg-[#00cc52] transition-colors">
              Ingresar
            </a>
          </div>

          <button className="md:hidden text-white" onClick={() => setIsMenuOpen(!isMenuOpen)}>
            {isMenuOpen ? <X /> : <Menu />}
          </button>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 overflow-hidden">
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-[#00ff66]/10 blur-[120px] -z-10 rounded-full" />
        
        <div className="max-w-7xl mx-auto px-6 grid lg:grid-cols-2 gap-16 items-center">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6 }}
          >
            <Badge className="mb-8">Análisis Activo · Fútbol Europeo</Badge>
            <h1 className="text-6xl md:text-8xl font-bold tracking-tighter leading-[0.9] mb-8">
              DETECTAMOS EL <br />
              <span className="text-[#00ff66] italic">ERROR</span> DE LA CASA.
            </h1>
            <p className="text-[#888] text-xl max-w-lg leading-relaxed mb-10">
              No apostamos por corazonadas. Valior usa modelos de <span className="text-white font-medium">Valor Esperado (EV)</span> para identificar cuotas mal calculadas por las casas de apuestas.
            </p>
            
            <div className="flex flex-wrap gap-6 items-center mb-12">
              <a href="/auth.html" className="bg-white text-black px-8 py-4 rounded-full font-bold uppercase tracking-widest text-sm hover:bg-[#00ff66] transition-all flex items-center gap-2">
                Ver señales de hoy <ArrowUpRight size={18} />
              </a>
              <a href="#track-record" className="font-mono text-xs uppercase tracking-widest text-[#888] hover:text-white transition-colors">
                +71.1% ROI Verificado
              </a>
            </div>

            <div className="grid grid-cols-3 gap-1 border-t border-[#222] pt-8">
              {[
                { label: 'Modelo', val: 'Poisson + xG' },
                { label: 'Señal VIP', val: 'EV ≥ 5%' },
                { label: 'Análisis', val: 'IA Real-time' },
              ].map((stat, i) => (
                <div key={i} className="space-y-1">
                  <span className="font-mono text-[9px] uppercase tracking-widest text-[#555]">{stat.label}</span>
                  <p className="text-sm font-bold text-white">{stat.val}</p>
                </div>
              ))}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="relative"
          >
            {/* Signal Widget */}
            <div className="bg-[#111] border border-[#222] rounded-2xl overflow-hidden shadow-2xl">
              <div className="bg-[#1a1a1a] px-6 py-3 border-b border-[#222] flex justify-between items-center">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-[#00ff66] animate-pulse" />
                  <span className="font-mono text-[10px] uppercase tracking-widest text-[#888]">Live Signal: Champions League</span>
                </div>
                <div className="px-2 py-0.5 rounded bg-[#00ff66]/10 border border-[#00ff66]/20 text-[#00ff66] text-[9px] font-bold uppercase tracking-widest">
                  VIP
                </div>
              </div>
              
              <div className="p-8">
                <div className="flex justify-between items-end mb-8">
                  <div className="space-y-1">
                    <h3 className="text-2xl font-bold tracking-tighter">Arsenal <span className="text-[#444] mx-2">vs</span> Real Madrid</h3>
                    <p className="text-[#555] font-mono text-[10px] uppercase tracking-widest">17 MAR 2026 · Emirates Stadium</p>
                  </div>
                  <div className="text-right">
                    <span className="text-xs text-[#888] block mb-1">Cuota</span>
                    <span className="text-2xl font-mono font-bold">1.88</span>
                  </div>
                </div>

                <div className="space-y-6">
                  <div>
                    <div className="flex justify-between text-[10px] uppercase tracking-widest text-[#555] mb-2 font-mono">
                      <span>Probabilidad Valior</span>
                      <span className="text-[#00ff66]">Edge Detectado</span>
                    </div>
                    <div className="h-1.5 bg-[#222] rounded-full overflow-hidden flex">
                      <div className="h-full bg-[#00ff66]" style={{ width: '41%' }} />
                      <div className="h-full bg-[#f59e0b]" style={{ width: '25%' }} />
                      <div className="h-full bg-[#ef4444]" style={{ width: '34%' }} />
                    </div>
                    <div className="flex justify-between mt-2 font-mono text-[10px]">
                      <span className="text-[#00ff66]">41% Local</span>
                      <span className="text-[#f59e0b]">25% Empate</span>
                      <span className="text-[#ef4444]">34% Visita</span>
                    </div>
                  </div>

                  <div className="bg-[#00ff66]/5 border border-[#00ff66]/10 rounded-xl p-4 flex items-center justify-between">
                    <div>
                      <span className="text-[9px] uppercase tracking-widest text-[#555] block mb-1">Mercado Sugerido</span>
                      <span className="text-sm font-bold">Over 2.5 Goles</span>
                    </div>
                    <div className="text-right">
                      <span className="text-[9px] uppercase tracking-widest text-[#555] block mb-1">Valor Esperado</span>
                      <span className="text-xl font-bold text-[#00ff66]">+6.2%</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-[#0a0a0a] px-6 py-3 border-t border-[#222] flex justify-between items-center font-mono text-[9px] text-[#444] uppercase tracking-widest">
                <span>Poisson + Elo + xG Analysis</span>
                <span>Update: 2s ago</span>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Stats Bar */}
      <section className="py-12 border-y border-[#222] bg-[#0d0d0d]">
        <div className="max-w-7xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8">
          {[
            { label: 'ROI Acumulado', val: '+71.1%', sub: '4 Jornadas', color: 'text-[#00ff66]' },
            { label: 'Picks Verificados', val: '26', sub: 'Track Record Público', color: 'text-white' },
            { label: 'Profit Total', val: '+18.48u', sub: 'Stake Plano 1u', color: 'text-white' },
            { label: 'Ligas Cubiertas', val: '4', sub: 'Top Europeas', color: 'text-white' },
          ].map((item, i) => (
            <div key={i} className="text-center md:text-left">
              <span className="font-mono text-[9px] uppercase tracking-widest text-[#555] block mb-2">{item.label}</span>
              <p className={`text-3xl font-bold tracking-tighter mb-1 ${item.color}`}>{item.val}</p>
              <span className="text-[10px] text-[#444] uppercase tracking-wider">{item.sub}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Bookmakers Ticker */}
      <section className="py-8 border-b border-[#222] bg-[#0a0a0a] overflow-hidden">
        <div className="max-w-7xl mx-auto px-6 flex flex-col items-center">
          <p className="font-mono text-[10px] uppercase tracking-widest text-[#555] mb-6 text-center">
            Escaneando cuotas en tiempo real en +20 casas de apuestas
          </p>
          <div className="flex flex-wrap justify-center gap-x-12 gap-y-6 opacity-50 grayscale hover:grayscale-0 transition-all duration-500">
            {BOOKMAKERS.map((bookie) => (
              <span key={bookie} className="text-xl font-bold tracking-tighter text-[#888] hover:text-white transition-colors cursor-default">
                {bookie}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* How it Works - Bento Grid */}
      <section id="modelo" className="py-24 max-w-7xl mx-auto px-6">
        <SectionHeader 
          eyebrow="Metodología"
          title="Tres pasos. Cero intuición."
          description="La ventaja matemática no requiere que seas un experto. Requiere usar la herramienta que procesa lo que el ojo humano ignora."
        />

        <div className="grid md:grid-cols-3 gap-6">
          <div className="bg-[#111] border border-[#222] p-8 rounded-2xl hover:border-[#333] transition-colors">
            <div className="w-10 h-10 bg-[#00ff66]/10 rounded-lg flex items-center justify-center text-[#00ff66] mb-6">
              <Database size={20} />
            </div>
            <h3 className="text-xl font-bold mb-4">Ingesta de Datos</h3>
            <p className="text-[#888] text-sm leading-relaxed mb-6">
              Procesamos Elo ratings, xG por temporada, forma reciente e historial H2H. Sin narrativas, solo datos crudos.
            </p>
            <div className="flex flex-wrap gap-2">
              {['Elo', 'xG', 'H2H', 'Live Odds'].map(tag => (
                <span key={tag} className="px-2 py-1 rounded bg-[#1a1a1a] border border-[#222] text-[9px] font-mono text-[#555] uppercase">{tag}</span>
              ))}
            </div>
          </div>

          <div className="bg-[#111] border border-[#222] p-8 rounded-2xl hover:border-[#333] transition-colors">
            <div className="w-10 h-10 bg-[#00ff66]/10 rounded-lg flex items-center justify-center text-[#00ff66] mb-6">
              <Zap size={20} />
            </div>
            <h3 className="text-xl font-bold mb-4">Cálculo de EV</h3>
            <p className="text-[#888] text-sm leading-relaxed mb-6">
              El modelo calcula la probabilidad real. Si la cuota de la casa es superior a nuestra probabilidad, hay <span className="text-white">Edge</span>.
            </p>
            <div className="bg-[#0a0a0a] p-3 rounded-lg border border-[#222] font-mono text-[11px] text-[#00ff66]">
              EV = (P_modelo × Cuota) - 1
            </div>
          </div>

          <div className="bg-[#111] border border-[#222] p-8 rounded-2xl hover:border-[#333] transition-colors">
            <div className="w-10 h-10 bg-[#00ff66]/10 rounded-lg flex items-center justify-center text-[#00ff66] mb-6">
              <Target size={20} />
            </div>
            <h3 className="text-xl font-bold mb-4">Filtro de Ruido</h3>
            <p className="text-[#888] text-sm leading-relaxed mb-6">
              Solo emitimos señales cuando el edge es estadísticamente significativo. Calidad sobre cantidad.
            </p>
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-[10px] uppercase tracking-widest">
                <div className="w-1.5 h-1.5 rounded-full bg-[#00ff66]" />
                <span className="text-white">EV ≥ 5% → VIP</span>
              </div>
              <div className="flex items-center gap-2 text-[10px] uppercase tracking-widest">
                <div className="w-1.5 h-1.5 rounded-full bg-[#f59e0b]" />
                <span className="text-[#888]">EV 1-4.9% → Análisis</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Track Record Section */}
      <section id="track-record" className="py-24 bg-[#0d0d0d] border-y border-[#222]">
        <div className="max-w-7xl mx-auto px-6">
          <SectionHeader 
            eyebrow="Transparencia"
            title="Lo que ganamos — y lo que perdimos."
            description="Nada se borra. Nada se edita. Si el modelo es bueno, los números lo demuestran solos. Aquí está la curva de rendimiento real."
          />

          <div className="grid lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2 bg-[#111] border border-[#222] rounded-2xl p-8">
              <div className="flex justify-between items-center mb-8">
                <h3 className="font-mono text-[10px] uppercase tracking-[0.2em] text-[#555]">Crecimiento de ROI (%)</h3>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-[#00ff66]" />
                    <span className="text-[10px] text-[#888] uppercase">Verificado</span>
                  </div>
                </div>
              </div>
              
              <div className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={ROI_DATA}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#222" vertical={false} />
                    <XAxis 
                      dataKey="name" 
                      stroke="#444" 
                      fontSize={10} 
                      tickLine={false} 
                      axisLine={false}
                      tick={{ fill: '#444' }}
                    />
                    <YAxis 
                      stroke="#444" 
                      fontSize={10} 
                      tickLine={false} 
                      axisLine={false}
                      tick={{ fill: '#444' }}
                    />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#111', border: '1px solid #333', borderRadius: '8px' }}
                      itemStyle={{ color: '#00ff66', fontSize: '12px', fontWeight: 'bold' }}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="roi" 
                      stroke="#00ff66" 
                      strokeWidth={3} 
                      dot={{ fill: '#00ff66', strokeWidth: 2, r: 4 }}
                      activeDot={{ r: 6, strokeWidth: 0 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="space-y-6">
              <div className="bg-[#111] border border-[#00ff66]/20 p-8 rounded-2xl relative overflow-hidden group">
                <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                  <TrendingUp size={80} className="text-[#00ff66]" />
                </div>
                <span className="font-mono text-[9px] uppercase tracking-widest text-[#555] block mb-2">Rendimiento Actual</span>
                <p className="text-5xl font-bold tracking-tighter text-[#00ff66] mb-2">+71.1%</p>
                <p className="text-[#888] text-xs leading-relaxed">
                  Basado en 26 picks auditados con stake plano de 1 unidad.
                </p>
              </div>

              <div className="bg-[#111] border border-[#222] p-8 rounded-2xl">
                <h4 className="text-sm font-bold mb-4 flex items-center gap-2">
                  <ShieldCheck size={16} className="text-[#00ff66]" />
                  ¿Por qué los perdedores?
                </h4>
                <p className="text-[#555] text-xs leading-relaxed">
                  Cualquier canal de Telegram dice tener 80% de acierto. Nosotros mostramos todo. Nuestro edge no necesita maquillaje.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Testimonials Section */}
      <section className="py-24 max-w-7xl mx-auto px-6">
        <SectionHeader 
          eyebrow="Comunidad"
          title="De apostadores a inversores."
          description="Usuarios reales que han dejado la intuición atrás y ahora operan basándose exclusivamente en Valor Esperado."
        />
        
        <div className="grid md:grid-cols-3 gap-6">
          {TESTIMONIALS.map((t, i) => (
            <div key={i} className="bg-[#111] border border-[#222] p-8 rounded-2xl hover:border-[#333] transition-all group">
              <div className="flex items-center gap-4 mb-6">
                <div className="w-12 h-12 rounded-full bg-[#1a1a1a] border border-[#333] flex items-center justify-center text-[#888] font-bold text-lg">
                  {t.name.charAt(0)}
                </div>
                <div>
                  <div className="flex items-center gap-1">
                    <h4 className="font-bold text-white">{t.name}</h4>
                    {t.verified && <CheckCircle2 size={14} className="text-[#00ff66]" />}
                  </div>
                  <span className="text-xs font-mono text-[#555]">{t.handle}</span>
                </div>
              </div>
              <p className="text-[#888] text-sm leading-relaxed group-hover:text-[#ccc] transition-colors">
                "{t.text}"
              </p>
            </div>
          ))}
        </div>

        {/* Incentive Banner */}
        <div className="mt-12 bg-gradient-to-r from-[#00ff66]/10 to-transparent border border-[#00ff66]/20 rounded-2xl p-8 flex flex-col md:flex-row items-center justify-between gap-8">
          <div>
            <h4 className="text-xl font-bold text-white mb-3 flex items-center gap-3">
              <Gift size={20} className="text-[#00ff66]" />
              Tu transparencia tiene recompensa.
            </h4>
            <p className="text-[#888] text-sm max-w-2xl leading-relaxed">
              Nuestro mayor activo es la verdad. Comparte tu experiencia honesta y tu track record usando Valior en tu red social favorita (X, Instagram, TikTok). Etiquétanos <span className="text-white font-mono">@ValiorApp</span> y obtén un <strong className="text-[#00ff66] font-normal">10% de descuento en tu suscripción PRO</strong>. Sin sorteos, recompensa directa.
            </p>
          </div>
          <button className="whitespace-nowrap bg-[#111] border border-[#333] hover:border-[#00ff66] text-white px-8 py-4 rounded-xl text-xs font-bold uppercase tracking-widest transition-all shadow-lg">
            Reclamar descuento
          </button>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="planes" className="py-24 max-w-7xl mx-auto px-6 border-t border-[#222]">
        <SectionHeader 
          eyebrow="Acceso"
          title="Empieza gratis. Escala cuando estés listo."
          description="El análisis base es gratuito para siempre. El plan PRO es para quienes buscan el edge completo en todas las ligas."
        />

        <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {/* Free Plan */}
          <div className="bg-[#111] border border-[#222] p-10 rounded-3xl flex flex-col">
            <div className="mb-8">
              <h3 className="text-xl font-bold mb-2">Gratuito</h3>
              <div className="flex items-baseline gap-1">
                <span className="text-4xl font-bold">$0</span>
                <span className="text-[#555] text-sm">/siempre</span>
              </div>
            </div>
            
            <div className="space-y-4 mb-10 flex-1">
              {[
                '2-3 análisis diarios con EV',
                'Probabilidades 1X2 del modelo',
                'Acceso permanente sin tarjeta',
              ].map(feat => (
                <div key={feat} className="flex items-center gap-3 text-sm text-[#888]">
                  <CheckCircle2 size={16} className="text-[#444]" />
                  {feat}
                </div>
              ))}
            </div>

            <a href="/auth.html" className="w-full py-4 rounded-xl border border-[#333] text-xs font-bold uppercase tracking-widest hover:bg-white hover:text-black transition-all block text-center">
              Crear Cuenta
            </a>
          </div>

          {/* PRO Plan */}
          <div className="bg-[#111] border border-[#00ff66]/30 p-10 rounded-3xl flex flex-col relative overflow-hidden">
            <div className="absolute top-0 right-0 bg-[#00ff66] text-black text-[9px] font-bold px-4 py-1 uppercase tracking-widest transform rotate-45 translate-x-8 translate-y-4">
              Recomendado
            </div>
            
            <div className="mb-8">
              <h3 className="text-xl font-bold mb-2 text-[#00ff66]">PRO Access</h3>
              <div className="flex items-baseline gap-1">
                <span className="text-4xl font-bold">$9.99</span>
                <span className="text-[#555] text-sm">/mes</span>
              </div>
            </div>
            
            <div className="space-y-4 mb-10 flex-1">
              {[
                'Todas las ligas europeas',
                'Mercados: Acceso total a todos los mercados',
                'Señales VIP (Edge ≥ 5%)',
                'Narrativa IA en español',
                'Historial auditado completo',
              ].map(feat => (
                <div key={feat} className="flex items-center gap-3 text-sm text-white">
                  <CheckCircle2 size={16} className="text-[#00ff66]" />
                  {feat}
                </div>
              ))}
            </div>

            <a href="/auth.html" className="w-full py-4 rounded-xl bg-[#00ff66] text-black text-xs font-bold uppercase tracking-widest hover:bg-[#00cc52] transition-all shadow-[0_0_20px_rgba(0,255,102,0.2)] block text-center">
              Unirse a la Beta
            </a>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="py-24 max-w-4xl mx-auto px-6">
        <SectionHeader 
          eyebrow="FAQ"
          title="Lo que probablemente estás pensando."
          description="Resolvemos las dudas más comunes sobre el uso de modelos matemáticos para apuestas deportivas."
        />
        <div className="mt-12">
          {FAQS.map((faq, i) => (
            <AccordionItem key={i} question={faq.q} answer={faq.a} />
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-[#222]">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-8">
          <div className="flex items-center gap-3">
            <Activity size={18} className="text-[#00ff66]" />
            <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-[#555]">
              Valior · El modelo que trabaja antes del pitazo.
            </span>
          </div>
          
          <div className="flex gap-8">
            {['Twitter', 'Telegram', 'Support'].map(item => (
              <a key={item} href="#" className="text-[10px] uppercase tracking-widest text-[#555] hover:text-white transition-colors">
                {item}
              </a>
            ))}
          </div>
        </div>
      </footer>
    </div>
  );
}
