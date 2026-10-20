import React from "react";
import { MapPin, ArrowRight } from "lucide-react";

export default function DestinationCards({ onSelectPrompt }) {
  const destinations = [
    {
      city: "Tokyo, Japan",
      tag: "Cultural & Futuristic",
      img: "https://images.unsplash.com/photo-1503899036084-c55cdd92da26?auto=format&fit=crop&w=600&q=80",
      query: "Plan a 5-day budget trip to Tokyo, Japan for 2 people with a total budget of $3000.",
    },
    {
      city: "Paris, France",
      tag: "Romantic & Opulent",
      img: "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&w=600&q=80",
      query: "I want a 3-day luxury weekend in Paris, France. Budget is flexible.",
    },
    {
      city: "Dubai, UAE",
      tag: "Luxury & Adventure",
      img: "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?auto=format&fit=crop&w=600&q=80",
      query: "Plan a 4-day trip to Dubai with desert safari and iconic skyline sightseeing.",
    },
    {
      city: "New York, USA",
      tag: "Metropolitan Energy",
      img: "https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?auto=format&fit=crop&w=600&q=80",
      query: "Plan a 4-day trip to New York City focusing on Broadway, museums, and food.",
    },
  ];

  return (
    <div className="my-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
          Featured Destinations (Quick Start)
        </h3>
        <span className="text-[11px] text-blue-400 font-medium">Click any card to launch</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {destinations.map((d, i) => (
          <div
            key={i}
            onClick={() => onSelectPrompt(d.query)}
            className="group relative bg-[#131b2e] border border-[#1e293b] hover:border-blue-500/50 rounded-2xl overflow-hidden cursor-pointer shadow-lg hover:shadow-blue-500/10 transition-all duration-300 hover:-translate-y-1"
          >
            {/* Image Header with Gradient Overlay */}
            <div className="h-32 w-full relative overflow-hidden">
              <img
                src={d.img}
                alt={d.city}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                loading="lazy"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-[#131b2e] via-transparent to-black/30" />
              <span className="absolute top-2.5 right-2.5 bg-black/60 backdrop-blur-md text-[10px] text-blue-300 font-semibold px-2 py-0.5 rounded-full border border-white/10">
                {d.tag}
              </span>
            </div>

            {/* Content Body */}
            <div className="p-3.5">
              <div className="flex items-center gap-1.5 text-white font-bold text-sm mb-1">
                <MapPin className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />
                <span className="truncate">{d.city}</span>
              </div>
              <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                {d.query}
              </p>

              <div className="mt-3 pt-2.5 border-t border-[#1e293b] flex items-center justify-between text-[11px] font-semibold text-blue-400 group-hover:text-blue-300">
                <span>Start Planning</span>
                <ArrowRight className="w-3.5 h-3.5 transform group-hover:translate-x-1 transition-transform" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
