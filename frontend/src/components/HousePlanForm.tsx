import React, { useState } from 'react';
import DOMPurify from 'dompurify';
import Modal from './Modal';
import LocationPicker from './LocationPicker';
import LoadingOverlay from './LoadingOverlay';

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
  // Plano Diretor
  taxa_ocupacao: number;              // percentual 0–100
  coeficiente_aproveitamento: number; // CA
  recuo_frontal: number;              // metros
  recuo_lateral: number;              // metros
  recuo_fundo: number;                // metros
  num_pavimentos: number;             // gabarito
  taxa_permeabilidade: number;        // percentual 0–100
}

interface TerrainData {
  min_elevation: number;
  max_elevation: number;
  height_difference: number;
  slope: number;
  slope_angle: number;
  coordinates: {
    lat: number;
    lng: number;
  };
}

interface HousePlanFormProps {
  onSubmit?: (svg: string) => void;
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Valores genéricos permissivos usados quando o usuário não quer configurar o plano diretor
const GENERIC_PLANO_DIRETOR = {
  taxa_ocupacao: 60,
  coeficiente_aproveitamento: 2.0,
  recuo_frontal: 3.0,
  recuo_lateral: 1.5,
  recuo_fundo: 1.5,
  num_pavimentos: 2,
  taxa_permeabilidade: 15,
};

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
    description: '',
    ...GENERIC_PLANO_DIRETOR,
  });
  const [usarPlanoDiretor, setUsarPlanoDiretor] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [showImageModal, setShowImageModal] = useState(false);
  const [svgContent, setSvgContent] = useState<string>('');
  const [imageUrl, setImageUrl] = useState<string>('');
  const [isLoadingImage, setIsLoadingImage] = useState(false);
  const [terrainData, setTerrainData] = useState<TerrainData | null>(null);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : type === 'number' ? Number(value) : value
    }));
  };

  const handleLocationSelect = (address: string) => {
    setFormData(prev => ({ ...prev, address }));
  };

  const handleTogglePlanoDiretor = (checked: boolean) => {
    setUsarPlanoDiretor(checked);
    if (!checked) {
      // Volta para os valores genéricos ao desativar
      setFormData(prev => ({ ...prev, ...GENERIC_PLANO_DIRETOR }));
    }
  };

  const handleMoreInfo = async () => {
    if (isLoadingImage) return;
    
    if (!formData.description.trim()) {
      setError('Por favor, preencha a descrição antes de gerar a visualização.');
      return;
    }

    setIsLoadingImage(true);

    try {
      let currentTerrainData = terrainData;

      if (formData.address) {
        const terrainResponse = await fetch(`${API_URL}/analyze-terrain?address=${encodeURIComponent(formData.address)}`);
        if (!terrainResponse.ok) throw new Error('Failed to analyze terrain');
        currentTerrainData = await terrainResponse.json();
        setTerrainData(currentTerrainData);
        localStorage.setItem('terrainData', JSON.stringify(currentTerrainData));
      }

      if (!currentTerrainData) {
        try {
          const stored = localStorage.getItem('terrainData');
          currentTerrainData = stored ? JSON.parse(stored) : null;
        } catch {
          currentTerrainData = null;
        }
      }

      if (!currentTerrainData || Object.keys(currentTerrainData).length === 0) {
        setError('Dados do terreno não disponíveis. Informe um endereço primeiro.');
        return;
      }

      const imageResponse = await fetch(`${API_URL}/generate-house-image`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          description: formData.description,
          terrain_data: currentTerrainData
        })
      });
      if (!imageResponse.ok) {
        const errorData = await imageResponse.json();
        throw new Error(errorData.detail || 'Failed to generate house image');
      }
      const { image_url } = await imageResponse.json();
      setImageUrl(image_url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoadingImage(false);
      setShowImageModal(true);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setImageUrl('');
    setTerrainData(null);

    try {
      // Generate house plan
      const response = await fetch(`${API_URL}/generate-house-plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          terrain_width: formData.terrain_width,
          terrain_height: formData.terrain_height,
          num_bedrooms: formData.num_bedrooms,
          num_bathrooms: formData.num_bathrooms,
          has_dining_room: formData.has_dining_room,
          has_garage: formData.has_garage,
          style: formData.style,
          taxa_ocupacao: formData.taxa_ocupacao / 100,
          coeficiente_aproveitamento: formData.coeficiente_aproveitamento,
          recuo_frontal: formData.recuo_frontal,
          recuo_lateral: formData.recuo_lateral,
          recuo_fundo: formData.recuo_fundo,
          num_pavimentos: formData.num_pavimentos,
          taxa_permeabilidade: formData.taxa_permeabilidade / 100,
        })
      });

      if (!response.ok) throw new Error('Failed to generate house plan');
      const svg = await response.text();
      setSvgContent(svg);
      setShowModal(true);
      if (onSubmit) onSubmit(svg);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-8">
      {(loading || isLoadingImage) && (
        <LoadingOverlay 
          message={loading ? "Gerando planta da casa..." : "Gerando visualização da casa..."} 
        />
      )}

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
            <div className="text-sm text-gray-500 mb-2">
              Clique no mapa para selecionar a localização
            </div>
            <LocationPicker onLocationSelect={handleLocationSelect} />
            {formData.address && (
              <div className="mt-2 text-sm text-gray-600">
                Localização selecionada: {formData.address}
              </div>
            )}
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

        {/* Plano Diretor */}
        <div className="border border-gray-200 rounded-lg p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-gray-700">Parâmetros do Plano Diretor</h3>
              <p className="text-xs text-gray-500 mt-0.5">
                {usarPlanoDiretor
                  ? 'Preencha conforme a zona do seu terreno. Consulte a prefeitura local.'
                  : 'Usando valores genéricos permissivos. Ative para informar os parâmetros do seu município.'}
              </p>
            </div>
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <span className="text-xs text-gray-600">Configurar</span>
              <div className="relative">
                <input
                  type="checkbox"
                  className="sr-only"
                  checked={usarPlanoDiretor}
                  onChange={e => handleTogglePlanoDiretor(e.target.checked)}
                />
                <div className={`w-10 h-6 rounded-full transition-colors ${usarPlanoDiretor ? 'bg-blue-600' : 'bg-gray-300'}`} />
                <div className={`absolute top-1 left-1 w-4 h-4 rounded-full bg-white shadow transition-transform ${usarPlanoDiretor ? 'translate-x-4' : ''}`} />
              </div>
            </label>
          </div>

          {!usarPlanoDiretor && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 bg-gray-50 rounded-lg p-3 text-xs text-gray-500">
              <span>TO: {GENERIC_PLANO_DIRETOR.taxa_ocupacao}%</span>
              <span>CA: {GENERIC_PLANO_DIRETOR.coeficiente_aproveitamento}</span>
              <span>Gabarito: {GENERIC_PLANO_DIRETOR.num_pavimentos} pav.</span>
              <span>Permeab.: {GENERIC_PLANO_DIRETOR.taxa_permeabilidade}%</span>
              <span>R. Frontal: {GENERIC_PLANO_DIRETOR.recuo_frontal}m</span>
              <span>R. Lateral: {GENERIC_PLANO_DIRETOR.recuo_lateral}m</span>
              <span>R. Fundo: {GENERIC_PLANO_DIRETOR.recuo_fundo}m</span>
            </div>
          )}

          {usarPlanoDiretor && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="space-y-1">
                  <label className="block text-xs font-medium text-gray-600">Taxa de Ocupação — TO (%)</label>
                  <input type="number" name="taxa_ocupacao" value={formData.taxa_ocupacao} onChange={handleInputChange}
                    className="block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200 px-3 py-2 text-sm"
                    min="1" max="100" step="1" />
                </div>
                <div className="space-y-1">
                  <label className="block text-xs font-medium text-gray-600">Coef. de Aproveitamento — CA</label>
                  <input type="number" name="coeficiente_aproveitamento" value={formData.coeficiente_aproveitamento} onChange={handleInputChange}
                    className="block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200 px-3 py-2 text-sm"
                    min="0.1" max="20" step="0.1" />
                </div>
                <div className="space-y-1">
                  <label className="block text-xs font-medium text-gray-600">Gabarito (nº de pavimentos)</label>
                  <input type="number" name="num_pavimentos" value={formData.num_pavimentos} onChange={handleInputChange}
                    className="block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200 px-3 py-2 text-sm"
                    min="1" max="30" step="1" />
                </div>
                <div className="space-y-1">
                  <label className="block text-xs font-medium text-gray-600">Taxa de Permeabilidade (%)</label>
                  <input type="number" name="taxa_permeabilidade" value={formData.taxa_permeabilidade} onChange={handleInputChange}
                    className="block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200 px-3 py-2 text-sm"
                    min="0" max="99" step="1" />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-1">
                  <label className="block text-xs font-medium text-gray-600">Recuo Frontal (m)</label>
                  <input type="number" name="recuo_frontal" value={formData.recuo_frontal} onChange={handleInputChange}
                    className="block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200 px-3 py-2 text-sm"
                    min="0" step="0.5" />
                </div>
                <div className="space-y-1">
                  <label className="block text-xs font-medium text-gray-600">Recuo Lateral (m)</label>
                  <input type="number" name="recuo_lateral" value={formData.recuo_lateral} onChange={handleInputChange}
                    className="block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200 px-3 py-2 text-sm"
                    min="0" step="0.5" />
                </div>
                <div className="space-y-1">
                  <label className="block text-xs font-medium text-gray-600">Recuo de Fundo (m)</label>
                  <input type="number" name="recuo_fundo" value={formData.recuo_fundo} onChange={handleInputChange}
                    className="block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200 px-3 py-2 text-sm"
                    min="0" step="0.5" />
                </div>
              </div>
            </div>
          )}
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
          <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(svgContent) }} />
          <div className="absolute top-4 right-4 flex gap-2">
            <button
              onClick={() => {
                const blob = new Blob([svgContent], { type: 'image/svg+xml' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'planta-casa.svg';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
              }}
              className="px-4 py-2 rounded-md bg-green-600 hover:bg-green-700 text-white transition-colors"
            >
              Download SVG
            </button>
            <button
              onClick={handleMoreInfo}
              disabled={isLoadingImage}
              className={`px-4 py-2 rounded-md transition-colors ${
                isLoadingImage
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700 text-white'
              }`}
            >
              {isLoadingImage ? 'Gerando...' : 'Mais Informações'}
            </button>
          </div>
        </div>
      </Modal>

      <Modal isOpen={showImageModal} onClose={() => setShowImageModal(false)} title="Visualização da Casa">
        <div className="space-y-4">
          {imageUrl && (
            <img 
              src={imageUrl} 
              alt="Visualização da casa" 
              className="w-full rounded-lg shadow-lg"
            />
          )}
          {terrainData && (
            <div className="bg-gray-50 p-4 rounded-lg">
              <h3 className="text-lg font-semibold mb-2">Informações do Terreno</h3>
              <pre className="text-sm text-gray-700 whitespace-pre-wrap">
                {JSON.stringify(terrainData, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
};

export default HousePlanForm; 