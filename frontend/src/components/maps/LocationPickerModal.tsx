import React, { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '../ui/dialog'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Label } from '../ui/label'
import { MapPin, Search, Navigation, Check, Compass, Info } from 'lucide-react'

export interface SelectedLocation {
  address_line?: string
  area: string
  city: string
  pincode?: string
  latitude: number
  longitude: number
  google_place_id?: string
  formatted_address: string
}

interface LocationPickerModalProps {
  isOpen: boolean
  onClose: () => void
  onSelectLocation: (loc: SelectedLocation) => void
  initialLocation?: {
    latitude?: number
    longitude?: number
    area?: string
    address_line?: string
  }
}

// Popular service hubs in Chennai with coordinates
const CHENNAI_HUBS = [
  { name: 'Anna Nagar East', lat: 13.0850, lng: 80.2150, pincode: '600102' },
  { name: 'Anna Nagar West', lat: 13.0890, lng: 80.2080, pincode: '600040' },
  { name: 'Shenoy Nagar', lat: 13.0780, lng: 80.2240, pincode: '600030' },
  { name: 'Kilpauk', lat: 13.0805, lng: 80.2410, pincode: '600010' },
  { name: 'T. Nagar (Panagal Park)', lat: 13.0418, lng: 80.2341, pincode: '600017' },
  { name: 'Nungambakkam', lat: 13.0604, lng: 80.2442, pincode: '600034' },
  { name: 'Chetpet', lat: 13.0718, lng: 80.2396, pincode: '600031' },
  { name: 'Vadapalani', lat: 13.0500, lng: 80.2100, pincode: '600026' },
  { name: 'Alwarpet', lat: 13.0336, lng: 80.2520, pincode: '600018' },
  { name: 'Mylapore', lat: 13.0368, lng: 80.2676, pincode: '600004' },
]

export const LocationPickerModal: React.FC<LocationPickerModalProps> = ({
  isOpen,
  onClose,
  onSelectLocation,
  initialLocation,
}) => {
  const [lat, setLat] = useState<number>(initialLocation?.latitude || 13.0850)
  const [lng, setLng] = useState<number>(initialLocation?.longitude || 80.2150)
  const [area, setArea] = useState<string>(initialLocation?.area || 'Anna Nagar East')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedHub, setSelectedHub] = useState<string>(initialLocation?.area || 'Anna Nagar East')

  useEffect(() => {
    if (initialLocation?.latitude && initialLocation?.longitude) {
      setLat(initialLocation.latitude)
      setLng(initialLocation.longitude)
      if (initialLocation.area) {
        setArea(initialLocation.area)
        setSelectedHub(initialLocation.area)
      }
    }
  }, [initialLocation, isOpen])

  const handleHubSelect = (hub: typeof CHENNAI_HUBS[0]) => {
    setLat(hub.lat)
    setLng(hub.lng)
    setArea(hub.name)
    setSelectedHub(hub.name)
  }

  const handleMapCanvasClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    // Map click pixel relative to center of visual area into nearby lat/lng offset
    const latOffset = (rect.height / 2 - y) * 0.0004
    const lngOffset = (x - rect.width / 2) * 0.0004

    const newLat = parseFloat((lat + latOffset).toFixed(6))
    const newLng = parseFloat((lng + lngOffset).toFixed(6))

    setLat(newLat)
    setLng(newLng)
  }

  const handleConfirm = () => {
    const matched = CHENNAI_HUBS.find((h) => h.name.toLowerCase() === area.toLowerCase())
    const pincode = matched ? matched.pincode : '600001'

    onSelectLocation({
      area: area || 'Chennai Central',
      city: 'Chennai',
      pincode,
      latitude: lat,
      longitude: lng,
      formatted_address: `${area}, Chennai, Tamil Nadu ${pincode}`,
      google_place_id: `kavis_loc_${Math.round(lat * 1000)}_${Math.round(lng * 1000)}`,
    })
    onClose()
  }

  const filteredHubs = CHENNAI_HUBS.filter((h) =>
    h.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl bg-white border-stone-200">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-stone-900 font-bold font-serif text-lg">
            <Compass className="w-5 h-5 text-amber-600" />
            <span>Select Delivery Location on Map</span>
          </DialogTitle>
          <DialogDescription className="text-xs text-stone-500">
            Pinpoint customer location to calculate delivery distance, verify driver zone, and enable one-tap driver navigation.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 my-2">
          {/* Search Hub */}
          <div className="relative">
            <Search className="w-4 h-4 text-stone-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <Input
              type="text"
              placeholder="Search locality or landmark in Chennai..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 text-sm"
            />
          </div>

          {/* Quick Hub Chips */}
          <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto py-1">
            {filteredHubs.map((hub) => (
              <button
                key={hub.name}
                type="button"
                onClick={() => handleHubSelect(hub)}
                className={`px-2.5 py-1 text-xs font-medium rounded-full border transition-all ${
                  selectedHub === hub.name
                    ? 'bg-amber-100 text-amber-900 border-amber-400 font-semibold shadow-xs'
                    : 'bg-stone-50 text-stone-600 border-stone-200 hover:bg-stone-100'
                }`}
              >
                {hub.name}
              </button>
            ))}
          </div>

          {/* Interactive Visual Map Canvas */}
          <div
            onClick={handleMapCanvasClick}
            className="relative h-64 w-full rounded-xl overflow-hidden border border-stone-300 bg-stone-100 cursor-crosshair shadow-inner group"
            style={{
              backgroundImage: `radial-gradient(#d6d3d1 1.5px, transparent 1.5px), radial-gradient(#e7e5e4 1.5px, #fafaf9 1.5px)`,
              backgroundSize: '24px 24px',
              backgroundPosition: '0 0, 12px 12px',
            }}
          >
            {/* Grid Map Simulation Decor */}
            <div className="absolute inset-0 opacity-40 pointer-events-none">
              <svg className="w-full h-full stroke-stone-300" xmlns="http://www.w3.org/2000/svg">
                <line x1="20%" y1="0" x2="20%" y2="100%" strokeWidth="2" strokeDasharray="4" />
                <line x1="50%" y1="0" x2="50%" y2="100%" strokeWidth="3" />
                <line x1="80%" y1="0" x2="80%" y2="100%" strokeWidth="2" strokeDasharray="4" />
                <line x1="0" y1="30%" x2="100%" y2="30%" strokeWidth="2" strokeDasharray="4" />
                <line x1="0" y1="50%" x2="100%" y2="50%" strokeWidth="3" />
                <line x1="0" y1="75%" x2="100%" y2="75%" strokeWidth="2" strokeDasharray="4" />
              </svg>
            </div>

            {/* Click instruction banner */}
            <div className="absolute top-2 left-2 z-10 bg-white/90 backdrop-blur px-2.5 py-1 rounded-md text-[11px] font-medium text-stone-600 shadow-sm border border-stone-200 pointer-events-none flex items-center gap-1.5">
              <Navigation className="w-3.5 h-3.5 text-amber-600" />
              <span>Click anywhere on the map to drop / adjust pin</span>
            </div>

            {/* Centered Map Pin Marker */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-full pointer-events-none transition-transform duration-150 group-hover:scale-110">
              <div className="relative flex flex-col items-center">
                <div className="bg-amber-600 text-white p-2 rounded-full shadow-lg border-2 border-white ring-4 ring-amber-500/30 animate-bounce">
                  <MapPin className="w-5 h-5 text-white" />
                </div>
                <div className="w-2.5 h-1 bg-stone-800/40 rounded-full blur-[1px] mt-0.5" />
              </div>
            </div>

            {/* Current Selected Label */}
            <div className="absolute bottom-2 right-2 z-10 bg-stone-900/90 text-white px-3 py-1.5 rounded-lg text-xs font-semibold shadow-md pointer-events-none">
              {area || 'Selected Location'}
            </div>
          </div>

          {/* Coordinate Detail readout */}
          <div className="grid grid-cols-2 gap-3 bg-stone-50 p-3 rounded-lg border border-stone-200 text-xs">
            <div>
              <Label className="text-[11px] text-stone-500 font-medium">Latitude</Label>
              <div className="font-mono font-semibold text-stone-800 mt-0.5">{lat}</div>
            </div>
            <div>
              <Label className="text-[11px] text-stone-500 font-medium">Longitude</Label>
              <div className="font-mono font-semibold text-stone-800 mt-0.5">{lng}</div>
            </div>
          </div>

          <div className="flex items-center gap-1.5 text-[11px] text-stone-500 bg-amber-50/70 p-2 rounded border border-amber-200/60">
            <Info className="w-3.5 h-3.5 text-amber-700 shrink-0" />
            <span>
              Coordinates are automatically transferred to driver delivery navigation and order distance verification.
            </span>
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" onClick={onClose} className="text-xs">
            Cancel
          </Button>
          <Button
            onClick={handleConfirm}
            className="bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold gap-1.5 shadow"
          >
            <Check className="w-4 h-4" />
            <span>Confirm Location</span>
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
