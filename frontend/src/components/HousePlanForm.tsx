import React, { useState } from 'react';
import Modal from './Modal';

interface HousePlanFormData {
  terrain_width: number;
  terrain_height: number;
  num_bedrooms: number;
  num_bathrooms: number;
  has_dining_room: boolean;
  has_garage: boolean;
  style: string;
  address: string;
  description: string;
}

interface HousePlanFormProps {
  onSubmit?: (svg: string) => void;
}

const HousePlanForm: React.FC<HousePlanFormProps> = ({ onSubmit }) => {
  const [formData, setFormData] = useState<HousePlanFormData>({
    terrain_width: 20,
    terrain_height: 30,
    num_bedrooms: 2,
    num_bathrooms: 1,
    has_dining_room: false,
    has_garage: false,
    style: 'modern',
    address: '',
    description: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [showImageModal, setShowImageModal] = useState(false);
  const [svgContent, setSvgContent] = useState<string>('');

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // First, analyze terrain if address is provided
      let terrainData = null;
      if (formData.address) {
        const terrainResponse = await fetch(`http://localhost:8000/analyze-terrain?address=${encodeURIComponent(formData.address)}`);
        if (!terrainResponse.ok) throw new Error('Failed to analyze terrain');
        terrainData = await terrainResponse.json();
        localStorage.setItem('terrainData', JSON.stringify(terrainData));
      }

      // Generate house plan
      const response = await fetch('http://localhost:8000/generate-house-plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          terrain_width: formData.terrain_width,
          terrain_height: formData.terrain_height,
          num_bedrooms: formData.num_bedrooms,
          num_bathrooms: formData.num_bathrooms,
          has_dining_room: formData.has_dining_room,
          has_garage: formData.has_garage,
          style: formData.style
        })
      });

      if (!response.ok) throw new Error('Failed to generate house plan');
      const svg = await response.text();
      setSvgContent(svg);
      setShowModal(true);
      if (onSubmit) onSubmit(svg);

      // Generate house image if we have terrain data and description
      if (terrainData && formData.description) {
        const imageResponse = await fetch('http://localhost:8000/generate-house-image', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            description: formData.description,
            terrain_data: terrainData
          })
        });
        if (!imageResponse.ok) throw new Error('Failed to generate house image');
        const { image_url } = await imageResponse.json();
        localStorage.setItem('houseImageUrl', image_url);
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-8">
      <form onSubmit={handleSubmit} className="space-y-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="space-y-2">
            <label className="block text-sm font-semibold text-gray-700">Largura do Terreno (m)</label>
            <input
              type="number"
              name="terrain_width"
              value={formData.terrain_width}
              onChange={handleInputChange}
              className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-colors px-4 py-3"
              min="1"
              step="0.1"
              required
            />
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-semibold text-gray-700">Comprimento do Terreno (m)</label>
            <input
              type="number"
              name="terrain_height"
              value={formData.terrain_height}
              onChange={handleInputChange}
              className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-colors px-4 py-3"
              min="1"
              step="0.1"
              required
            />
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-semibold text-gray-700">Número de Quartos</label>
            <input
              type="number"
              name="num_bedrooms"
              value={formData.num_bedrooms}
              onChange={handleInputChange}
              className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-colors px-4 py-3"
              min="1"
              required
            />
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-semibold text-gray-700">Número de Banheiros</label>
            <input
              type="number"
              name="num_bathrooms"
              value={formData.num_bathrooms}
              onChange={handleInputChange}
              className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-colors px-4 py-3"
              min="1"
              required
            />
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-semibold text-gray-700">Estilo</label>
            <select
              name="style"
              value={formData.style}
              onChange={handleInputChange}
              className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-colors px-4 py-3"
            >
              <option value="modern">Moderno</option>
              <option value="traditional">Tradicional</option>
              <option value="compact">Compacto</option>
            </select>
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-semibold text-gray-700">Endereço do Terreno</label>
            <input
              type="text"
              name="address"
              value={formData.address}
              onChange={handleInputChange}
              className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-colors px-4 py-3"
              placeholder="Digite o endereço do terreno"
            />
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-semibold text-gray-700">Descrição da Casa</label>
            <textarea
              name="description"
              value={formData.description}
              onChange={handleInputChange}
              className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-colors px-4 py-3"
              placeholder="Descreva como você imagina sua casa"
              rows={3}
            />
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className="flex items-center">
            <input
              type="checkbox"
              name="has_dining_room"
              checked={formData.has_dining_room}
              onChange={handleInputChange}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <label className="ml-2 block text-sm text-gray-700">Sala de Jantar</label>
          </div>

          <div className="flex items-center">
            <input
              type="checkbox"
              name="has_garage"
              checked={formData.has_garage}
              onChange={handleInputChange}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <label className="ml-2 block text-sm text-gray-700">Garagem</label>
          </div>
        </div>

        {error && (
          <div className="text-red-600 text-sm mt-2">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-gradient-to-r from-blue-600 to-blue-700 text-white font-semibold py-3 px-6 rounded-lg hover:from-blue-700 hover:to-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <div className="flex items-center justify-center">
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Gerando Planta...
            </div>
          ) : (
            'Gerar Planta'
          )}
        </button>
      </form>

      <Modal isOpen={showModal} onClose={() => setShowModal(false)} title="Planta da Casa">
        <div className="relative">
          <div dangerouslySetInnerHTML={{ __html: svgContent }} />
          <button
            onClick={() => setShowImageModal(true)}
            className="absolute top-4 right-4 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors"
          >
            Mais Informações
          </button>
        </div>
      </Modal>

      <Modal isOpen={showImageModal} onClose={() => setShowImageModal(false)} title="Visualização da Casa">
        <div className="space-y-4">
          <img 
            src={localStorage.getItem('houseImageUrl') || ''} 
            alt="Visualização da casa" 
            className="w-full rounded-lg shadow-lg"
          />
          {localStorage.getItem('terrainData') && (
            <div className="bg-gray-50 p-4 rounded-lg">
              <h3 className="text-lg font-semibold mb-2">Informações do Terreno</h3>
              <pre className="text-sm text-gray-700 whitespace-pre-wrap">
                {JSON.stringify(JSON.parse(localStorage.getItem('terrainData') || '{}'), null, 2)}
              </pre>
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
};

export default HousePlanForm; 