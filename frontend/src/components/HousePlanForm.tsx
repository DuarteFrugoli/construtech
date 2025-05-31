import React, { useState } from 'react';
import axios from 'axios';
import Modal from './Modal';

interface HousePlanFormProps {
  onGenerate: (svg: string) => void;
}

const HousePlanForm: React.FC<HousePlanFormProps> = ({ onGenerate }) => {
  const [formData, setFormData] = useState({
    terrain_width: 10,
    terrain_height: 15,
    num_bedrooms: 2,
    num_bathrooms: 1,
    has_dining_room: false,
    has_garage: false,
    style: 'modern',
    gemini_api_key: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewSvg, setPreviewSvg] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
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
      const response = await axios.post('http://localhost:8000/generate-house-plan', formData, {
        headers: {
          'Content-Type': 'application/json'
        }
      });

      const svgContent = response.data;
      setPreviewSvg(svgContent);
      setIsModalOpen(true);
      onGenerate(svgContent);
    } catch (err) {
      setError('Failed to generate house plan. Please try again.');
      console.error('Error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto">
      <form onSubmit={handleSubmit} className="space-y-8 bg-white p-8 rounded-2xl shadow-xl border border-gray-100">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="space-y-2">
            <label className="block text-sm font-semibold text-gray-700">Terrain Width (m)</label>
            <input
              type="number"
              name="terrain_width"
              value={formData.terrain_width}
              onChange={handleInputChange}
              className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-colors px-4 py-3"
              min="1"
              required
            />
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-semibold text-gray-700">Terrain Height (m)</label>
            <input
              type="number"
              name="terrain_height"
              value={formData.terrain_height}
              onChange={handleInputChange}
              className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-colors px-4 py-3"
              min="1"
              required
            />
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-semibold text-gray-700">Number of Bedrooms</label>
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
            <label className="block text-sm font-semibold text-gray-700">Number of Bathrooms</label>
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
            <label className="block text-sm font-semibold text-gray-700">House Style</label>
            <select
              name="style"
              value={formData.style}
              onChange={handleInputChange}
              className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-colors px-4 py-3"
            >
              <option value="modern">Modern</option>
              <option value="traditional">Traditional</option>
              <option value="compact">Compact</option>
            </select>
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-semibold text-gray-700">Gemini API Key</label>
            <input
              type="password"
              name="gemini_api_key"
              value={formData.gemini_api_key}
              onChange={handleInputChange}
              className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-colors px-4 py-3"
              placeholder="Optional"
            />
          </div>
        </div>

        <div className="flex items-center space-x-8 pt-4">
          <div className="flex items-center">
            <input
              type="checkbox"
              name="has_dining_room"
              checked={formData.has_dining_room}
              onChange={handleInputChange}
              className="h-5 w-5 text-blue-600 focus:ring-2 focus:ring-blue-200 border-gray-300 rounded transition-colors"
            />
            <label className="ml-3 block text-sm font-medium text-gray-700">Include Dining Room</label>
          </div>

          <div className="flex items-center">
            <input
              type="checkbox"
              name="has_garage"
              checked={formData.has_garage}
              onChange={handleInputChange}
              className="h-5 w-5 text-blue-600 focus:ring-2 focus:ring-blue-200 border-gray-300 rounded transition-colors"
            />
            <label className="ml-3 block text-sm font-medium text-gray-700">Include Garage</label>
          </div>
        </div>

        {error && (
          <div className="text-red-600 text-sm bg-red-50 p-4 rounded-lg border border-red-100">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full flex justify-center py-4 px-6 border border-transparent rounded-xl shadow-sm text-base font-semibold text-white bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
        >
          {loading ? (
            <div className="flex items-center">
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Generating...
            </div>
          ) : (
            'Generate House Plan'
          )}
        </button>
      </form>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="House Plan Preview"
      >
        {previewSvg && (
          <div className="flex justify-center items-center">
            <div dangerouslySetInnerHTML={{ __html: previewSvg }} />
          </div>
        )}
      </Modal>
    </div>
  );
};

export default HousePlanForm; 