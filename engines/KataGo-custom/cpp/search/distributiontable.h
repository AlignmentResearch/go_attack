#ifndef SEARCH_DISTRIBUTIONTABLE_H
#define SEARCH_DISTRIBUTIONTABLE_H

#include "../core/global.h"

struct DistributionTable {
  double* pdfTable;
  double* cdfTable;
  int size;
  double minZ;
  double maxZ;

  DistributionTable(std::function<double(double)> pdf, std::function<double(double)> cdf, double minZ, double maxZ, int size);
  ~DistributionTable();

  DistributionTable(const DistributionTable& other) = delete;
  DistributionTable& operator=(const DistributionTable& other) = delete;

  inline void getPdfCdf(double z, double& pdf, double& cdf) const {
    double d = (size-1) * (z-minZ) / (maxZ-minZ);
    if(d <= 0) {
      pdf = 0.0;
      cdf = 0.0;
      return;
    }
    int idx = (int)d;
    if(idx >= size-1) {
      pdf = 0.0;
      cdf = 1.0;
      return;
    }
    double lambda = d - idx;
    double yp0 = pdfTable[idx];
    double yp1 = pdfTable[idx+1];
    double yc0 = cdfTable[idx];
    double yc1 = cdfTable[idx+1];
    pdf = yp0 + lambda * (yp1 - yp0);
    cdf = yc0 + lambda * (yc1 - yc0);
  };

  inline double getPdf(double z) const {
    double d = (size-1) * (z-minZ) / (maxZ-minZ);
    if(d <= 0)
      return 0.0;
    int idx = (int)d;
    if(idx >= size-1)
      return 0.0;
    double lambda = d - idx;
    double y0 = pdfTable[idx];
    double y1 = pdfTable[idx+1];
    return y0 + lambda * (y1 - y0);
  };

  inline double getCdf(double z) const {
    double d = (size-1) * (z-minZ) / (maxZ-minZ);
    if(d <= 0)
      return 0.0;
    int idx = (int)d;
    if(idx >= size-1)
      return 1.0;
    double lambda = d - idx;
    double y0 = cdfTable[idx];
    double y1 = cdfTable[idx+1];
    return y0 + lambda * (y1 - y0);
  };
};


#endif  // SEARCH_DISTRIBUTION_TABLE_H_
