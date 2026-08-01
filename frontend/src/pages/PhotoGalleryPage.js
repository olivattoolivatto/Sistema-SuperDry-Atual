import React, { useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { CheckCircle, Camera, AlertTriangle, Loader2, Image as ImageIcon } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

function PhotoGrid({ photos, label, colorClass }) {
  if (!photos || photos.length === 0) return null;
  return (
    <div>
      <p className={`text-xs font-semibold uppercase tracking-wide mb-2 ${colorClass}`}>{label}</p>
      <div className="grid grid-cols-2 gap-2">
        {photos.map((p, i) => (
          <a key={i} href={p.url} target="_blank" rel="noopener noreferrer" className="block">
            <img
              src={p.url}
              alt={`${label} ${i + 1}`}
              className="w-full h-32 object-cover rounded-lg border border-gray-200 hover:opacity-90 transition-opacity"
              onError={e => { e.target.style.display = 'none'; }}
            />
          </a>
        ))}
      </div>
    </div>
  );
}

export default function PhotoGalleryPage() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${BACKEND_URL}/api/gallery/${token}`);
      if (!r.ok) throw new Error('Link inválido ou expirado');
      setData(await r.json());
    } catch (e) {
      setError(e.message || 'Erro ao carregar galeria.');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="bg-white rounded-xl shadow p-6 max-w-sm w-full text-center">
          <AlertTriangle className="w-10 h-10 text-red-500 mx-auto mb-3" />
          <p className="text-gray-800 font-medium">{error}</p>
        </div>
      </div>
    );
  }

  const hasAnyPhoto = data.items.some(
    item => item.before.length > 0 || item.after.length > 0 || item.damage.length > 0
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-[#1F4E8C] text-white px-4 py-4">
        <p className="text-xs opacity-70 uppercase tracking-wide mb-0.5">{data.company_name}</p>
        <h1 className="text-base font-bold flex items-center gap-2">
          <Camera className="w-4 h-4" /> Registro do Serviço
        </h1>
        <p className="text-xs opacity-80 mt-0.5">
          Cliente: {data.client_name}
        </p>
      </div>

      <div className="max-w-lg mx-auto px-4 py-5 space-y-4">

        {/* Conclusão */}
        <div className="bg-green-50 border border-green-200 rounded-xl p-4 flex items-start gap-3">
          <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-green-800">Serviço concluído!</p>
            <p className="text-xs text-green-700 mt-0.5">
              Abaixo você encontra as fotos do antes e depois de cada item. Toque nas imagens para ampliar.
            </p>
          </div>
        </div>

        {/* Items */}
        {!hasAnyPhoto && (
          <div className="bg-white rounded-xl border border-gray-200 p-6 text-center">
            <ImageIcon className="w-8 h-8 text-gray-300 mx-auto mb-2" />
            <p className="text-sm text-gray-500">Nenhuma foto registrada para este serviço.</p>
          </div>
        )}

        {data.items.map(item => {
          const hasPhotos = item.before.length > 0 || item.after.length > 0 || item.damage.length > 0;
          if (!hasPhotos) return null;
          return (
            <div key={item.item_id} className="bg-white rounded-xl border border-gray-200 p-4 space-y-4">
              <h3 className="text-sm font-semibold text-gray-900">{item.service_name}</h3>

              <PhotoGrid photos={item.before} label="Antes do serviço" colorClass="text-blue-600" />
              <PhotoGrid photos={item.damage} label="Danos pré-existentes" colorClass="text-red-600" />
              <PhotoGrid photos={item.after} label="Depois do serviço" colorClass="text-green-600" />
            </div>
          );
        })}

        <p className="text-xs text-center text-gray-400 pb-4">
          Obrigado pela confiança! Qualquer dúvida, entre em contato conosco.
        </p>
      </div>
    </div>
  );
}
