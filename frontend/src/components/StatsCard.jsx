

/**
 * Reusable Statistics Card Component
 */
const StatsCard = ({ title, value, icon: Icon, color = 'blue', trend = null }) => {
  const colorClasses = {
    blue: 'text-blue-500',
    green: 'text-green-500',
    red: 'text-red-500',
    purple: 'text-purple-500',
    yellow: 'text-yellow-500',
    gray: 'text-gray-500',
  };

  const iconColor = colorClasses[color] || colorClasses.blue;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-slate-600 mb-1">{title}</p>
          <p className="text-3xl font-bold text-slate-900">{value}</p>
          
          {trend && (
            <div className={`mt-2 flex items-center text-sm ${
              trend > 0 ? 'text-green-600' : trend < 0 ? 'text-red-600' : 'text-gray-600'
            }`}>
              <span>{trend > 0 ? '↑' : trend < 0 ? '↓' : '→'}</span>
              <span className="ml-1">{Math.abs(trend)}% from last period</span>
            </div>
          )}
        </div>
        
        {Icon && (
          <div className="ml-4">
            <Icon className={`w-10 h-10 ${iconColor}`} />
          </div>
        )}
      </div>
    </div>
  );
};

export default StatsCard;