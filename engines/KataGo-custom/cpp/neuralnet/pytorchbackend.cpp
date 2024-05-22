#include "../neuralnet/pytorchbackend.h"

#include <cassert>
#include <sstream>

#include <ATen/autocast_mode.h>
#include <torch/csrc/jit/codegen/cuda/interface.h>

#include "../core/fileutils.h"
#include "../core/global.h"
#include "../neuralnet/modelversion.h"

using namespace torch::indexing;

namespace TorchNeuralNet {

namespace {

// HACK(ANONYMOUS_AUTHOR): We should write the model version and max model board size
// when exporting the model. For now we'll just hard code the values.
constexpr int MAX_BOARD_LEN = 19;
constexpr int MODEL_VERSION = 14;
const int NUM_SPATIAL_FEATURES = NNModelVersion::getNumSpatialFeatures(MODEL_VERSION);
const int NUM_GLOBAL_FEATURES = NNModelVersion::getNumGlobalFeatures(MODEL_VERSION);

void logModelForwardFailure(ComputeHandle* handle, InputBuffers* inputBuffers) {
  if (handle->logger != nullptr) {
    std::stringstream str;
    str << "Model evaluation failed with model " << getModelName(&handle->model) << " on input:";
    for (const auto& input: inputBuffers->modelInputs) {
      str << '\n' << input;
    }
    handle->logger->write(str.str());
  }
}

bool getUseFP16(enabled_t useFP16Mode) {
  return useFP16Mode == enabled_t::True;
}

// These wrappers for copying inputs and outputs are needed because the
// underlying data types of the `torch::Tensor`s are not known until runtime.
void copyInputsWithSymmetry(const float* src, torch::Tensor dst, int nSize, int hSize, int wSize, int cSize, bool useNHWC, int symmetry) {
  switch (dst.scalar_type()) {
    case torch::kFloat16:
      // Note: this call with at::Half is significantly slower than this
      // call with float and may make FP16 overall slower than FP32.
      return SymmetryHelpers::copyInputsWithSymmetry(src, dst.data_ptr<at::Half>(), nSize, hSize, wSize, cSize, useNHWC, symmetry);
    case torch::kFloat32:
      return SymmetryHelpers::copyInputsWithSymmetry(src, dst.data_ptr<float>(), nSize, hSize, wSize, cSize, useNHWC, symmetry);
    default:
      ASSERT_UNREACHABLE;
  }
}

void copyInputs(const float* src, torch::Tensor dst, int nSize) {
  switch (dst.scalar_type()) {
    case torch::kFloat16:
      std::copy(src, src + nSize, dst.data_ptr<at::Half>());
      return;
    case torch::kFloat32:
      std::copy(src, src + nSize, dst.data_ptr<float>());
      return;
    default:
      ASSERT_UNREACHABLE;
  }
}

void copyOutputsWithSymmetry(const torch::Tensor src, float* dst, int nSize, int hSize, int wSize, int symmetry) {
  switch (src.scalar_type()) {
    case torch::kFloat16:
      return SymmetryHelpers::copyOutputsWithSymmetry(src.data_ptr<at::Half>(), dst, nSize, hSize, wSize, symmetry);
    case torch::kFloat32:
      return SymmetryHelpers::copyOutputsWithSymmetry(src.data_ptr<float>(), dst, nSize, hSize, wSize, symmetry);
    default:
      ASSERT_UNREACHABLE;
  }
}

}  // namespace

LoadedModel::LoadedModel(const std::string& filename)
  : model(torch::jit::load(filename))
  , modelName(filename) {}

LoadedModel::LoadedModel(const LoadedModel& other)
  : modelName(other.modelName) {
  {
    const std::lock_guard<std::mutex> guard(other.cloneMutex);
    model = other.model.clone();
  }
}

LoadedModel* loadModelFile(const std::string& file, const std::string& expectedSha256) {
  if (expectedSha256.size() != 0) {
    throw StringError("Checking sha256 for PyTorch models is not yet implemented.\n");
  }
  if (!FileUtils::exists(file)) {
    throw IOError("File does not exist: " + file);
  }
  return new LoadedModel(file);
}

void freeLoadedModel(LoadedModel* model) {
  delete model;
}

std::string getModelName(const LoadedModel* model) {
  return model->modelName;
}

int getModelVersion(const LoadedModel*) {
  return MODEL_VERSION;
}

ComputeContext::ComputeContext(int nnXLen_, int nnYLen_, bool useFP16_)
  : nnXLen(nnXLen_)
  , nnYLen(nnYLen_)
  , useFP16(useFP16_) {
}

ComputeContext* createComputeContext(
  const std::vector<int>& gpuIdxs,
  Logger* logger,
  int nnXLen,
  int nnYLen,
  const std::string& openCLTunerFile,
  const std::string& homeDataDirOverride,
  bool openCLReTunePerBoardSize,
  enabled_t useFP16Mode,
  enabled_t useNHWCMode,
  const LoadedModel* loadedModel
) {
  (void)gpuIdxs;
  (void)logger;
  (void)openCLTunerFile;
  (void)homeDataDirOverride;
  (void)openCLReTunePerBoardSize;
  (void)loadedModel;
  if (useNHWCMode != enabled_t::False) {
    throw StringError("useNHWC is not yet implemented for PyTorch.");
  }
  const bool useFP16 = getUseFP16(useFP16Mode);
  assert(nnXLen <= MAX_BOARD_LEN);
  assert(nnYLen <= MAX_BOARD_LEN);

  ComputeContext* context = new ComputeContext(nnXLen, nnYLen, useFP16);
  return context;
}

void freeComputeContext(ComputeContext* context) {
  delete context;
}

ComputeHandle::ComputeHandle(
    const ComputeContext* context,
    const LoadedModel* model_,
    Logger* logger_,
    int maxBatchSize_,
    int gpuIdxForThisThread
)
  : model(*model_)
  , device(torch::Device(at::kCUDA, gpuIdxForThisThread))
  , logger(logger_)
  , maxBatchSize(maxBatchSize_)
  , nnXLen(context->nnXLen)
  , nnYLen(context->nnYLen)
  , useFP16(context->useFP16) {
    model.model.eval();
    model.model.to(device);
  }

ComputeHandle* createComputeHandle(
  ComputeContext* context,
  const LoadedModel* loadedModel,
  Logger* logger,
  int maxBatchSize,
  bool requireExactNNLen,
  bool inputsUseNHWC,
  int gpuIdxForThisThread,
  int serverThreadIdx
) {
  (void)requireExactNNLen;
  (void)serverThreadIdx;

  if (inputsUseNHWC) {
    throw StringError("inputsUseNHWC is not yet implemented for PyTorch.");
  }
  if (gpuIdxForThisThread == -1) {
    gpuIdxForThisThread = 0;
  }

  return new ComputeHandle(context, loadedModel, logger, maxBatchSize, gpuIdxForThisThread);
}

void freeComputeHandle(ComputeHandle* gpuHandle) {
  delete gpuHandle;
}

InputBuffers::InputBuffers(int maxBatchSize, enabled_t useFP16Mode) {
  const bool useFP16 = getUseFP16(useFP16Mode);
  const auto dataType = useFP16 ? torch::kFloat16 : torch::kFloat32;
  hostSpatialInputs = torch::empty({maxBatchSize, NUM_SPATIAL_FEATURES, MAX_BOARD_LEN, MAX_BOARD_LEN}, {dataType});
  hostGlobalInputs = torch::empty({maxBatchSize, NUM_GLOBAL_FEATURES}, {dataType});
  const size_t NUM_INPUTS = 2;
  modelInputs.reserve(NUM_INPUTS);
}

InputBuffers* createInputBuffers(const LoadedModel* loadedModel, int maxBatchSize, int nnXLen, int nnYLen, enabled_t useFP16Mode) {
  (void)loadedModel;
  (void)nnXLen;
  (void)nnYLen;
  return new InputBuffers(maxBatchSize, useFP16Mode);
}

void freeInputBuffers(InputBuffers* inputBuffers) {
  delete inputBuffers;
}

void getOutput(
  ComputeHandle* gpuHandle,
  InputBuffers* inputBuffers,
  int numBatchEltsFilled,
  NNResultBuf** inputBufs,
  std::vector<NNOutput*>& outputs
) {
  const int batchSize = numBatchEltsFilled;
  assert(batchSize <= gpuHandle->maxBatchSize);
  assert(batchSize > 0);
  const int nnXLen = gpuHandle->nnXLen;
  const int nnYLen = gpuHandle->nnYLen;
  if (nnXLen != MAX_BOARD_LEN || nnYLen != MAX_BOARD_LEN) {
    // The PyTorch model assumes that smaller board sizes' inputs are formatted
    // like in the following example channel-0 spatial input (signifying which
    // locations are on the board) for a 5x5 input:
    //   1 1 1 1 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0
    //   1 1 1 1 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0
    //   1 1 1 1 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0
    //   1 1 1 1 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0
    //   1 1 1 1 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0
    //   0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
    //   ...
    //   0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
    //
    // If nnXLen and nnYLen are set to 5 instead of MAX_BOARD_LEN==19,
    // KataGo populates the inputs as
    //   1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
    //   1 1 1 1 1 1 0 0 0 0 0 0 0 0 0 0 0 0 0
    //   0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
    //   ...
    //   0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
    //
    // The other backends handle this but I (ANONYMOUS_AUTHOR) haven't investigated how.
    // For now we'll just enforce that nnXLen and nnYLen are 19. If a user wants
    // to play on a 5x5 board, they should include 19 in the bSizes config
    // parameter (and set its bSizeRelProbs to 0 if they don't actually want any
    // 19x19 games), otherwise we throw an exception here.
    throw StringError(Global::strprintf("Board len not yet supported: %d x %d", nnXLen, nnYLen));
  }
  constexpr bool INPUTS_USE_NHWC = false;

  const auto& spatialInputs = inputBuffers->hostSpatialInputs;
  const auto& globalInputs = inputBuffers->hostGlobalInputs;
  for (int row = 0; row < batchSize; row++) {
    copyInputsWithSymmetry(inputBufs[row]->rowSpatial, spatialInputs[row], 1, nnYLen, nnXLen, NUM_SPATIAL_FEATURES, INPUTS_USE_NHWC, inputBufs[row]->symmetry);
    const float* rowGlobal = inputBufs[row]->rowGlobal;
    copyInputs(rowGlobal, globalInputs[row], NUM_GLOBAL_FEATURES);
  }

  auto& modelInputs = inputBuffers->modelInputs;
  modelInputs.clear();
  modelInputs.emplace_back(spatialInputs.index({Slice(0, batchSize)}).to(gpuHandle->device));
  modelInputs.emplace_back(globalInputs.index({Slice(0, batchSize)}).to(gpuHandle->device));

  c10::IValue modelOutput;
  {
    torch::NoGradGuard no_grad;
    try {
      modelOutput = gpuHandle->model.model.forward(modelInputs);
    } catch (const c10::Error&) {
      logModelForwardFailure(gpuHandle, inputBuffers);
      throw;
    } catch (const std::runtime_error& err) {
      if (std::string(err.what()).find("RuntimeError: Input type") != std::string::npos) {
        // If the error message looks like "RuntimeError: Input type
        // (CUDAHalfType) and weight type (CUDAFloatType) should be the same",
        // the error may be that the user did not set useFP16-N to match whether
        // TorchScript model nnModelFileN was exported with FP16.
        if (gpuHandle->logger != nullptr) {
          gpuHandle->logger->write("HINT: Is useFP16 set correctly for each TorchScript bot?");
        }
      } else {
        logModelForwardFailure(gpuHandle, inputBuffers);
      }
      throw;
    }
  }

  const auto& modelOutputs = modelOutput.toTupleRef().elements();
  at::Tensor policyOutputs = modelOutputs[0].toTensor();
  const at::Tensor& valueOutputs = modelOutputs[1].toTensor().to(at::kCPU);
  const at::Tensor& miscValueOutputs = modelOutputs[2].toTensor().to(at::kCPU);
  const at::Tensor& moreMiscValueOutputs = modelOutputs[3].toTensor().to(at::kCPU);
  at::Tensor ownershipOutputs;

  const bool has_optimistic_policy = policyOutputs.size(1) > 1;
  at::Tensor policies = policyOutputs.index({Slice(), 0});
  at::Tensor optimisticPolicyDiffs;
  if (has_optimistic_policy) {
    optimisticPolicyDiffs = policyOutputs.index({Slice(), 1}).sub_(policies);
  }
  for (int row = 0; row < batchSize; row++) {
    NNOutput* output = outputs[row];

    const int numPolicyValues = nnYLen * nnXLen + 1;
    at::Tensor policy = policies.index({row, Slice(0, numPolicyValues)});
    if (has_optimistic_policy) {
      const float policyOptimism = (float)inputBufs[row]->policyOptimism;
      // final policy = policy + (policy - optimisticPolicy) * policyOptimism
      policy.add_(optimisticPolicyDiffs.index({row, Slice(0, numPolicyValues)}), policyOptimism);
    }
    policy = policy.to(at::kCPU).contiguous();
    copyOutputsWithSymmetry(policy, output->policyProbs, 1, nnYLen, nnXLen, inputBufs[row]->symmetry);
    // Copy the policy output for passing as well.
    output->policyProbs[nnYLen * nnXLen] = policy[nnYLen * nnXLen].item<float>();

    const auto& valueOutput = valueOutputs[row];
    output->whiteWinProb = valueOutput[0].item<float>();
    output->whiteLossProb = valueOutput[1].item<float>();
    output->whiteNoResultProb = valueOutput[2].item<float>();

    const auto& miscValueOutput = miscValueOutputs[row];
    output->whiteScoreMean = miscValueOutput[0].item<float>();
    output->whiteScoreMeanSq = miscValueOutput[1].item<float>();
    output->whiteLead = miscValueOutput[2].item<float>();
    output->varTimeLeft = miscValueOutput[3].item<float>();

    const auto& moreMiscValueOutput = moreMiscValueOutputs[row];
    output->shorttermWinlossError = moreMiscValueOutput[0].item<float>();
    output->shorttermScoreError = moreMiscValueOutput[1].item<float>();

    if (output->whiteOwnerMap != NULL) {
      if (!ownershipOutputs.defined()) {
        ownershipOutputs = modelOutputs[4].toTensor().to(at::kCPU);
      }
      copyOutputsWithSymmetry(ownershipOutputs[row], output->whiteOwnerMap, 1, nnYLen, nnXLen, inputBufs[row]->symmetry);
    }
  }
}

}  // namespace TorchNeuralNet
